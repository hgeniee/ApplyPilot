import httpx


async def send_slack_message(webhook_url: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(webhook_url, json={"text": text})
        response.raise_for_status()

