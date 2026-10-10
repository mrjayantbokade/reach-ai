# ReachAI

ReachAI is a terminal-based contact and outreach intelligence agent. A LangGraph
agent decides which LangChain tool to call; deterministic services and PostgreSQL
perform data validation, matching, and persistence.

## What it can do

- Save or update contacts with business and personal email addresses and phones.
- Infer a company from a business-email domain when no company is stated.
- Search companies, including close spelling matches, and retrieve company contacts.
- List companies, contacts, emails, phones, opportunities, referrals, outreach events, and source records.
- Record opportunities, referrals, and inbound/outbound outreach events.
- Find uncontacted company contacts and rank outreach candidates.

## Architecture

```text
Terminal → LangGraph agent → OpenAI-compatible chat model → LangChain tools
                                                       → services → PostgreSQL
```

The model chooses tools and produces the final response. Tools do not accept
arbitrary SQL; they use SQLAlchemy repositories and services.

## Local setup

Prerequisites: Python 3.11+, PostgreSQL, and either an OpenAI-compatible local
model server or an OpenRouter API key.

```bash
git clone <your-github-repository-url>
cd reachai
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Edit `.env`. It is ignored by Git and must never be committed.

### Local model example

```env
DATABASE_URL=postgresql+psycopg://<database-user>@localhost:5432/<database-name>
LLM_PROVIDER=openai_compatible
LLM_MODEL=<local-model-name>
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=<local-api-key-or-placeholder>
```

### OpenRouter example

```env
DATABASE_URL=postgresql+psycopg://<database-user>@localhost:5432/<database-name>
OPENROUTER_API_KEY=<your-openrouter-key>
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

When an OpenRouter key is set, it is used first. If its request fails, ReachAI
falls back to the local-model settings. The CLI displays the active provider and
model at startup.

Run migrations and start the agent:

```bash
alembic upgrade head
PYTHONPATH=src python -m reachai agent
```

## Example requests

```text
save Person Name <person@gmail.com>, person.name@company.com
get contacts at Example Corp
list all saved companies
show emails for Example Corp
which contacts at Example Corp have never been contacted?
```

## Using Codex or Claude Code

Codex and Claude Code can help set up and change this project, but they do not
automatically receive your database credentials or model API keys. After cloning
the repository, open the project in either tool and ask it to follow this README.

Before allowing either tool to run the app, you must create `.env` from
`.env.example` and supply the required local values. Keep `.env`, API keys, and
database credentials out of commits, prompts, and pull requests.

## Database

Alembic manages PostgreSQL tables for companies, contacts, contact emails,
contact phones, contact sources, opportunities, outreach events, and referrals.

## Verification

Run the test suite only when you want automated verification:

```bash
pytest
```
