# Enterprise AI Operating Model Agent Lab v0.3

A working backend-based prototype with **five actual LLM role agents** and an independent, deterministic governance policy engine.

## Run locally

Requires Python 3.9+ and an OpenAI API key with API billing enabled. No third-party Python packages required.

macOS/Linux:

```bash
export OPENAI_API_KEY="your-key-here"
python3 server.py
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key-here"
python server.py
```

Open **http://localhost:8000** in your browser. Do not double-click `index.html` because the backend must run.

Optional: set `OPENAI_MODEL` (defaults to `gpt-4.1-mini`) and `PORT` (defaults to `8000`).

## How it works

- The frontend calls `GET /api/status` to confirm server and API key configuration.
- `POST /api/run` calls the OpenAI chat-completions API once for each of five roles: Business Manager, AI Champion, Governance Officer, Enterprise Architect, Executive Sponsor.
- Each role sees the scenario, enforced governance decision, and previous role assessments. Responses are generated on demand.
- **The policy engine is authoritative.** Tier 1 read-only internal work can be delegated under mission command; sensitive and write-capable cases escalate. LLM opinions cannot override this.
- You can export the resulting audit record.

## Deployment

Deploy the directory to any host capable of running Python with a long-running HTTP server (Azure App Service, Render, Railway, VM). Configure `OPENAI_API_KEY` as a server-side secret and start with `python server.py`. Set `PORT` as required by the host. This is a prototype, not production hardened: before public deployment, add authentication, rate limits, usage budgets, persistent storage, and request concurrency limits. **Do not expose the unprotected server publicly with a funded API key.**

## Limitations

Agents generate real model responses only when a valid key and network connection are provided. This package cannot supply credentials or a public hosted URL. Scenarios are synthetic; no real enterprise systems are controlled. Agent conversations are sequential, not independently running background workers. The governance rules are a small illustrative subset of the playbook.
