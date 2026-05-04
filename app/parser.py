import httpx


async def fetch_job_text(url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(jina_url)
        response.raise_for_status()
        text = response.text.strip()

    if not text:
        raise ValueError("Jina Reader returned an empty response.")
    return text
