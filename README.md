# PipelineMedic

> Push → CI fails → POST log to this API → Groq/LLM explains the failure → Auto-fix PR + Telegram alert to your team.

---

## Problem Statement / Idea

**What is the problem?**
Every modern software team relies on CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins, etc.) to test and ship code. When a pipeline fails, developers have to manually dig through hundreds of lines of raw logs to figure out:

- What actually broke (a missing dependency? a flaky test? a config typo? an import error?)
- Where to fix it (which file, which line)
- How to fix it safely without breaking anything else

This manual log triage is slow, repetitive, and a massive drain on engineering time — especially for small teams and during late-night on-call incidents.

**Why is it important?**
- A single broken build can block an entire team from merging or deploying.
- Most CI failures fall into a small number of well-known patterns (missing packages, off-by-one test failures, typos, import errors) that are *mechanically* fixable.
- Developer focus time is the most expensive resource in any engineering org. Context-switching into a log-dump destroys flow.

**Who are the target users?**
- Solo developers and indie hackers shipping fast on GitHub.
- Hackathon and student teams who can't afford dedicated DevOps.
- Small-to-mid engineering teams who want an "AI on-call engineer" for their CI pipeline.
- Any team that already uses **GitHub Actions + Telegram/Slack** and wants zero-friction failure triage.

---

## Proposed Solution

**What are we building?**
**PipelineMedic** is an AI-powered CI/CD failure doctor. When your GitHub Actions workflow fails, it automatically:

1. **Ingests** the failed build log via a simple webhook (`POST /webhook`).
2. **Diagnoses** the root cause using **Groq (LLaMA 3.3 70B)**, with a deterministic rule-based fallback for offline demos.
3. **Auto-patches** the code when the fix is small, surgical, and high-confidence (missing deps, clear logic bugs, imports, typos).
4. **Verifies the fix in a sandbox** — optionally spins up a **Vercel Sandbox** (ephemeral Firecracker microVM) and re-runs the failing test before opening any PR, so we never push broken fixes.
5. **Opens a GitHub Pull Request** with the patch, reviewers, and a human-readable explanation.
6. **Notifies the team on Telegram** with the diagnosis, confidence, risk, and a direct link to the PR.

**How does it solve the problem?**
Instead of a developer reading logs at 11 PM, PipelineMedic turns *"your build failed"* into *"your build failed, here's exactly why, here's the fix, and by the way — here's the PR already opened and sandbox-verified."* The human stays in the loop (they review and merge), but the grunt work is gone.

**What makes our solution unique?**
- **Sandbox-verified autofixes** — we don't just suggest a patch, we *run it* inside an isolated Vercel Sandbox microVM with pytest before opening a PR. No more "AI suggested a fix that didn't actually work."
- **LLM + rules hybrid** — works fully offline via a deterministic fallback when Groq isn't available (great for demos, air-gapped envs, and cost control).
- **Full LLM observability** — every Groq generation is traced via **Langfuse** with token usage and cost tracking baked in.
- **Zero-infra deploy** — one-click deploy to **Vercel** as a serverless webhook. No Kubernetes, no Docker, no babysitting.
- **Tight Telegram loop** — alerts land where your team already lives, with the PR link attached.

---

## Features

- **`POST /webhook` CI ingest** — accepts `{ repository, log | log_text }` and returns JSON with `root_cause`, `fix`, `confidence`, `risk`, and `fixable`.
- **Groq-powered diagnosis** (LLaMA 3.3 70B Versatile) with a strict JSON contract.
- **Rule-based fallback** — deterministic pattern matcher for missing deps, imports, common pytest/jest failures; used whenever `GROQ_API_KEY` is absent.
- **Automatic GitHub PR creation** — when the fix is fixable and `confidence > 0.7`, PipelineMedic commits a patch to a new branch and opens a PR via the GitHub REST API.
- **Vercel Sandbox self-verification** — optional Firecracker microVM that runs the AI-generated fix + regression test with pytest; PR is only opened on green.
- **Telegram alerts** — structured, human-readable message with diagnosis, confidence, risk, and PR link (when created).
- **Langfuse observability** — automatic tracing of every LLM call with prompt/completion tokens and cost.
- **Next.js dashboard** (`/web`) — a modern React 19 + TanStack Query frontend to browse past incidents and diagnoses.
- **Demo-ready** — `demo.sh` and a sample failing repo under `examples/demo-repo/` for end-to-end judge demos.

---

## Tech Stack

**Frontend**
- [Next.js 15](https://nextjs.org/) (App Router, Turbopack)
- [React 19](https://react.dev/)
- [TanStack Query v5](https://tanstack.com/query)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [TypeScript 5](https://www.typescriptlang.org/)

**Backend**
- [Python 3.13](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- Pure REST webhook — no framework lock-in.

**Database / Storage**
- Lightweight JSON memory under `data/` for demos.
- (Pluggable — can be swapped for Vercel Postgres / Neon / Upstash in production.)

**APIs / Services**
- [Groq API](https://groq.com/) — LLaMA 3.3 70B Versatile inference.
- [GitHub REST API](https://docs.github.com/en/rest) — branch, commit, and PR creation.
- [Telegram Bot API](https://core.telegram.org/bots/api) — team alerts.
- [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) — ephemeral microVM fix verification.
- [Langfuse](https://langfuse.com/) — LLM tracing, token usage, and cost analytics.

**Tools / Libraries**
- `requests` — HTTP client for Groq, GitHub, Telegram.
- `python-dotenv` — environment management.
- `langfuse` — LLM observability SDK.
- `@tanstack/react-query` — server-state management on the dashboard.
- **Vercel** — hosting for the serverless webhook and the Next.js dashboard.

---

## Project Setup Instructions

### Prerequisites
- Python **3.11+** (3.13 recommended)
- Node.js **20+** (only if running the dashboard under `/web`)
- A [Groq API key](https://console.groq.com/keys) (free tier works)
- A Telegram bot token + chat id ([guide](https://core.telegram.org/bots#how-do-i-create-a-bot))
- *(Optional)* A GitHub PAT with `Contents` + `Pull Requests` scope for real auto-PRs.

### 1. Clone the repository

```bash
git clone https://github.com/Aqib053/hacktofuture4-D01.git
cd hacktofuture4-D01
```

### 2. Install backend dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env` and fill in **at least**:

```env
GROQ_API_KEY=gsk_...
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=your_chat_id
```

Optional for auto-PRs and sandbox verification:

```env
GITHUB_TOKEN=ghp_...
VERCEL_TOKEN=...
VERCEL_TEAM_ID=...
VERCEL_PROJECT_ID=...
```

### 3.1 Optional: Telegram alert on every local commit

If you want a Telegram message whenever you run `git commit` locally:

```bash
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/install-git-hook.ps1
```

This installs `.githooks/post-commit` into `.git/hooks/post-commit`.
The hook uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from your `.env`.
Disable commit alerts any time with:

```env
TELEGRAM_COMMIT_NOTIFY_ENABLED=false
```

### 4. Run the backend

```bash
python main.py
# API running at http://127.0.0.1:8000
```

Health check: `GET http://127.0.0.1:8000/` should return `{"status":"ok", ...}`.

### 5. Try the demo

In another terminal:

```bash
chmod +x demo.sh
./demo.sh
```

This POSTs a sample failing CI log to `/webhook` and you should see:
- A JSON diagnosis in the terminal
- A Telegram alert (if configured)
- A PR opened against your target repo (if `GITHUB_TOKEN` is set)

### 6. *(Optional)* Run the Next.js dashboard

```bash
cd web
npm install
npm run dev
# Dashboard at http://localhost:3000
```

### 7. Deploy to Vercel (public webhook)

```bash
npm i -g vercel
vercel --prod
```

Set the same env vars in the Vercel project dashboard, then point your GitHub Actions workflow at:

```
https://<your-project>.vercel.app/webhook
```

Store that URL as a repo secret named `PIPELINEMEDIC_WEBHOOK_URL`.

---

## Repository Structure

```
PipeLinMedic2.0/
├── main.py                 # FastAPI webhook + Groq + GitHub PR + Telegram + Sandbox
├── app.py                  # Vercel entrypoint
├── requirements.txt
├── vercel.json
├── demo.sh                 # End-to-end local demo script
├── .env.example
├── examples/
│   └── demo-repo/          # Sample failing repo for judge demos
├── web/                    # Next.js 15 dashboard (App Router)
└── data/                   # JSON incident memory
```

---

## License

MIT — use it, fork it, ship it.
