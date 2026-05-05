from __future__ import annotations

from datetime import date, timedelta
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


def _headers(settings: Settings) -> dict:
    return {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _plain_text(items: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in items)


def _select_name(prop: dict) -> Optional[str]:
    value = prop.get("select")
    if not value:
        return None
    return value.get("name")


def _page_to_job_summary(page: dict) -> dict:
    props = page.get("properties", {})
    deadline = props.get("마감일", {}).get("date") or {}
    return {
        "company_name": _plain_text(props.get("기업명", {}).get("title", [])),
        "role": _select_name(props.get("직군", {})),
        "platform": _select_name(props.get("플랫폼", {})),
        "status": _select_name(props.get("상태", {})),
        "deadline": deadline.get("start"),
        "url": props.get("공고 URL", {}).get("url"),
        "notion_url": page.get("url"),
    }


async def create_job_page(job: ExtractedJob, settings: Settings) -> str:
    payload = {
        "parent": {"database_id": settings.notion_database_id},
        "properties": build_page_properties(job),
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.notion.com/v1/pages",
            headers=_headers(settings),
            json=payload,
        )
        response.raise_for_status()
        return response.json()["id"]


async def query_deadline_reminders(settings: Settings, today: Optional[date] = None) -> list[dict]:
    base_date = today or date.today()
    target_dates = [
        (base_date + timedelta(days=1)).isoformat(),
        (base_date + timedelta(days=3)).isoformat(),
    ]
    payload = {
        "filter": {
            "or": [
                {"property": "마감일", "date": {"equals": target_dates[0]}},
                {"property": "마감일", "date": {"equals": target_dates[1]}},
            ]
        },
        "sorts": [{"property": "마감일", "direction": "ascending"}],
    }
    url = f"https://api.notion.com/v1/databases/{settings.notion_database_id}/query"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=_headers(settings), json=payload)
        response.raise_for_status()
        data = response.json()

    return [_page_to_job_summary(page) for page in data.get("results", [])]
