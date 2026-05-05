from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from httpx import HTTPStatusError

from app.agent import extract_job
from app.config import get_settings
from app.notion_client import create_job_page, query_deadline_reminders
from app.parser import fetch_job_text
from app.schemas import ParseJobRequest, ParseJobResponse
from app.slack_notifier import build_deadline_message, send_slack_message


app = FastAPI(title="Job Agent")


INDEX_HTML = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Job Agent</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #1f2328;
      --muted: #667085;
      --line: #d9dee7;
      --primary: #155eef;
      --primary-dark: #0f49bd;
      --danger: #b42318;
      --ok: #027a48;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      width: min(920px, calc(100% - 32px));
      margin: 0 auto;
      padding: 48px 0;
    }
    header {
      margin-bottom: 28px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    form {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: end;
    }
    label {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
      font-weight: 600;
    }
    input {
      width: 100%;
      height: 44px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 12px;
      font-size: 15px;
      color: var(--text);
      background: #fff;
    }
    input:focus {
      outline: 2px solid rgba(21, 94, 239, 0.18);
      border-color: var(--primary);
    }
    button {
      height: 44px;
      border: 0;
      border-radius: 6px;
      padding: 0 18px;
      background: var(--primary);
      color: #fff;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }
    button:hover { background: var(--primary-dark); }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.65;
    }
    #status {
      min-height: 24px;
      margin: 14px 0 0;
      font-size: 14px;
      color: var(--muted);
    }
    #status.ok { color: var(--ok); }
    #status.error { color: var(--danger); }
    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }
    .secondary {
      background: #344054;
    }
    .secondary:hover {
      background: #1d2939;
    }
    .result {
      display: none;
      margin-top: 18px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 16px;
    }
    .field {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fcfcfd;
      min-width: 0;
    }
    .field.full {
      grid-column: 1 / -1;
    }
    .key {
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }
    .value {
      overflow-wrap: anywhere;
      line-height: 1.45;
      font-size: 15px;
    }
    a {
      color: var(--primary);
      text-decoration: none;
    }
    a:hover { text-decoration: underline; }
    @media (max-width: 720px) {
      main { padding: 28px 0; }
      form { grid-template-columns: 1fr; }
      button { width: 100%; }
      .grid { grid-template-columns: 1fr; }
      .field.full { grid-column: auto; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Job Agent</h1>
      <p>채용공고 URL을 붙여넣으면 공고를 읽고 Notion 채용 공고 트래커에 저장합니다.</p>
    </header>

    <section class="panel">
      <form id="job-form">
        <div>
          <label for="url">채용공고 URL</label>
          <input id="url" name="url" type="url" placeholder="https://linkareer.com/activity/318628" required />
        </div>
        <button id="submit" type="submit">공고 추가</button>
      </form>
      <div id="status"></div>
      <div class="actions">
        <button id="reminder" class="secondary" type="button">마감 알림 보내기</button>
        <button id="slack-test" class="secondary" type="button">Slack 테스트</button>
      </div>
    </section>

    <section id="result" class="panel result" aria-live="polite">
      <p id="saved"></p>
      <div class="grid">
        <div class="field">
          <div class="key">기업명</div>
          <div id="company" class="value"></div>
        </div>
        <div class="field">
          <div class="key">직군</div>
          <div id="role" class="value"></div>
        </div>
        <div class="field">
          <div class="key">플랫폼</div>
          <div id="platform" class="value"></div>
        </div>
        <div class="field">
          <div class="key">마감일</div>
          <div id="deadline" class="value"></div>
        </div>
        <div class="field full">
          <div class="key">키워드</div>
          <div id="keywords" class="value"></div>
        </div>
        <div class="field full">
          <div class="key">메모</div>
          <div id="memo" class="value"></div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const form = document.querySelector("#job-form");
    const input = document.querySelector("#url");
    const button = document.querySelector("#submit");
    const reminderButton = document.querySelector("#reminder");
    const slackTestButton = document.querySelector("#slack-test");
    const statusEl = document.querySelector("#status");
    const resultEl = document.querySelector("#result");

    function setStatus(message, type = "") {
      statusEl.textContent = message;
      statusEl.className = type;
    }

    function setText(id, value) {
      document.querySelector(id).textContent = value || "-";
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      resultEl.style.display = "none";
      button.disabled = true;
      setStatus("공고를 읽고 있습니다. 페이지에 따라 10-30초 정도 걸릴 수 있습니다.");

      try {
        const response = await fetch("/jobs/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: input.value.trim() }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "요청 처리에 실패했습니다.");
        }

        const job = data.job;
        setStatus("Notion 저장이 완료됐습니다.", "ok");
        document.querySelector("#saved").innerHTML =
          `Notion page id: <code>${data.notion_page_id}</code>`;
        setText("#company", job.company_name);
        setText("#role", job.role);
        setText("#platform", job.platform);
        setText("#deadline", job.deadline);
        setText("#keywords", (job.keywords || []).join(", "));
        setText("#memo", job.memo);
        resultEl.style.display = "block";
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        button.disabled = false;
      }
    });

    reminderButton.addEventListener("click", async () => {
      reminderButton.disabled = true;
      setStatus("Notion에서 D-1, D-3 마감 공고를 조회하고 Slack으로 보내는 중입니다.");
      try {
        const response = await fetch("/reminders/deadlines", { method: "POST" });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "알림 발송에 실패했습니다.");
        }
        setStatus(`Slack 알림을 보냈습니다. 대상 공고 ${data.count}개.`, "ok");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        reminderButton.disabled = false;
      }
    });

    slackTestButton.addEventListener("click", async () => {
      slackTestButton.disabled = true;
      setStatus("Slack 테스트 메시지를 보내는 중입니다.");
      try {
        const response = await fetch("/slack/test", { method: "POST" });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Slack 테스트에 실패했습니다.");
        }
        setStatus(data.message, "ok");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        slackTestButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict:
    return {"ok": True}


def _get_slack_webhook_url() -> str:
    webhook_url = get_settings().slack_webhook_url
    if not webhook_url:
        raise HTTPException(status_code=400, detail="SLACK_WEBHOOK_URL is not configured.")
    return webhook_url


@app.post("/jobs/parse", response_model=ParseJobResponse)
async def parse_job(request: ParseJobRequest) -> ParseJobResponse:
    settings = get_settings()
    source_url = str(request.url)
    try:
        text = await fetch_job_text(source_url)
        job = await extract_job(text, source_url, settings)
        notion_page_id = await create_job_page(job, settings)
        return ParseJobResponse(job=job, notion_page_id=notion_page_id)
    except HTTPStatusError as exc:
        message = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/slack/test")
async def slack_test() -> dict:
    try:
        await send_slack_message(_get_slack_webhook_url(), "Job Agent Slack 연결 테스트입니다.")
        return {"ok": True, "message": "Slack 테스트 메시지를 보냈습니다."}
    except HTTPStatusError as exc:
        message = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/reminders/deadlines")
async def send_deadline_reminders() -> dict:
    settings = get_settings()
    try:
        jobs = await query_deadline_reminders(settings)
        message = build_deadline_message(jobs)
        await send_slack_message(_get_slack_webhook_url(), message)
        return {"ok": True, "count": len(jobs), "message": message}
    except HTTPStatusError as exc:
        message = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
