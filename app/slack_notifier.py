import httpx


async def send_slack_message(webhook_url: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(webhook_url, json={"text": text})
        response.raise_for_status()


def build_deadline_message(jobs: list[dict]) -> str:
    if not jobs:
        return "오늘 기준 마감 D-1 또는 D-3 채용공고가 없습니다."

    lines = ["채용공고 마감 알림"]
    for job in jobs:
        company = job.get("company_name") or "기업명 미상"
        role = job.get("role") or "직군 미상"
        deadline = job.get("deadline") or "마감일 미상"
        status = job.get("status") or "상태 미상"
        url = job.get("url") or job.get("notion_url") or ""
        line = f"- {deadline} | {company} | {role} | {status}"
        if url:
            line = f"{line}\n  {url}"
        lines.append(line)
    return "\n".join(lines)
