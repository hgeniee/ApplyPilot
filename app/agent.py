import json
import re

import httpx

from app.config import Settings
from app.schemas import ExtractedJob


SYSTEM_PROMPT = """You extract structured Korean job posting data.
Return only valid JSON with this exact schema:
{
  "company_name": "string",
  "role": "string",
  "platform": "string or null",
  "deadline": "YYYY-MM-DD or null",
  "keywords": ["string"],
  "memo": "short Korean summary string or null",
  "interview_questions": "string or null"
}
If a value is unknown, use null except keywords should be an empty array."""


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


async def extract_job(text: str, source_url: str, settings: Settings) -> ExtractedJob:
    payload = {
        "model": settings.model_name,
        "max_tokens": 1000,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    "아래 채용공고에서 기업명, 직군, 플랫폼, 마감일, 핵심 키워드, "
                    "메모, 예상 면접 질문을 추출해줘.\n\n"
                    f"공고 URL: {source_url}\n\n"
                    f"공고 원문:\n{text[:12000]}"
                ),
            }
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "Authorization": f"Bearer {settings.anthropic_api_key}",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(settings.model_api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("content", [])
    if content and isinstance(content, list):
        result_text = "".join(
            item.get("text", "") for item in content if item.get("type") == "text"
        )
    else:
        result_text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    parsed = _extract_json(result_text)
    parsed["source_url"] = source_url
    return ExtractedJob.model_validate(parsed)

