from __future__ import annotations

from typing import Optional

import httpx

from app.config import Settings
from app.schemas import ExtractedJob


NOTION_VERSION = "2022-06-28"


def _rich_text(value: Optional[str]) -> list[dict]:
    if not value:
        return []
    return [{"type": "text", "text": {"content": value[:2000]}}]


def _select(value: Optional[str]) -> Optional[dict]:
    if not value:
        return None
    return {"name": value[:100]}


def build_page_properties(job: ExtractedJob) -> dict:
    memo_parts = []
    if job.memo:
        memo_parts.append(job.memo)
    if job.keywords:
        memo_parts.append("키워드: " + ", ".join(job.keywords))

    properties: dict = {
        "기업명": {"title": _rich_text(job.company_name)},
        "직군": {"select": _select(job.role)},
        "상태": {"select": {"name": "지원예정"}},
        "공고 URL": {"url": job.source_url},
        "메모": {"rich_text": _rich_text("\n".join(memo_parts))},
        "면접 질문": {"rich_text": _rich_text(job.interview_questions)},
    }

    if job.platform:
        properties["플랫폼"] = {"select": _select(job.platform)}
    if job.deadline:
        properties["마감일"] = {"date": {"start": job.deadline}}

    return properties


async def create_job_page(job: ExtractedJob, settings: Settings) -> str:
    payload = {
        "parent": {"database_id": settings.notion_database_id},
        "properties": build_page_properties(job),
    }
    headers = {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()["id"]
