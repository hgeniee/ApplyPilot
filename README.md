# Job Agent

채용공고 URL을 Jina Reader로 텍스트화하고, Claude 호환 Messages API로 구조화한 뒤 Notion DB에 저장하는 FastAPI MVP입니다.

## Setup

```bash
python3 -m pip install -r requirements.txt
```

`.env`에 아래 값이 필요합니다.

```bash
NOTION_API_KEY=...
NOTION_DATABASE_ID=...
ANTHROPIC_API_KEY=...
SLACK_WEBHOOK_URL=...
MODEL_API_BASE_URL=https://your-gateway-host.example
MODEL_API_ENDPOINT=/v1/gateway/claude/v1/messages/
MODEL_NAME=claude-sonnet-4-6
```

## Run

```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open the UI:

```text
http://127.0.0.1:8000
```

## API

```bash
curl -X POST http://127.0.0.1:8000/jobs/parse \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/job-posting"}'
```

Send a Slack test message:

```bash
curl -X POST http://127.0.0.1:8000/slack/test
```

Send deadline reminders for Notion jobs due in 1 or 3 days:

```bash
curl -X POST http://127.0.0.1:8000/reminders/deadlines
```

Notion DB 속성명은 현재 아래 이름을 기준으로 저장합니다.

```text
기업명, 직군, 플랫폼, 마감일, 상태, 공고 URL, 메모, 면접 질문
```
