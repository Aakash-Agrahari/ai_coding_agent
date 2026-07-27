# AI Coding Agent

An autonomous Python AI agent that explores the [`node-easy-notes-app`](https://github.com/callicoder/node-easy-notes-app) repository and implements improvements for organising and searching notes — with no human guidance beyond the initial user request.

---

## Architecture

```
ai-coding-agent/
├── agent.py            ← Main entry point
├── requirements.txt    ← Python dependencies
├── .env.example        ← API key template
├── README.md           ← This file
└── workspace/
    └── node-easy-notes-app/   ← Auto-cloned target repository
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | [Google Antigravity SDK](https://pypi.org/project/google-antigravity/) |
| LLM | Gemini (default model via Antigravity SDK) |
| Language | Python 3.11+ |
| Target app | Node.js + Express + Mongoose (MongoDB) |

---

## Agent Workflow

The agent follows a strict **Explore → Plan → Implement → Validate → Commit → Summarise** loop, enforced through the system prompt:

```
1. EXPLORE
   │  list_files('.')          → discover all source files
   │  read_file(each file)     → understand model, routes, controllers
   ▼
2. PLAN
   │  create_plan(text)        → saves execution_plan.txt + prints to console
   ▼
3. IMPLEMENT
   │  write_file(path, content) → rewrites modified files in full
   ▼
4. VALIDATE
   │  run_shell('node --check <file>') → syntax check every changed JS file
   ▼
5. GIT COMMIT
   │  run_shell('git add -A')
   │  run_shell('git commit -m "feat: ..."')
   ▼
6. SUMMARISE
      summarise_changes(text)  → saves changes_summary.txt + prints to console
```

### Custom Tools

The agent is equipped with five Python-backed tools:

| Tool | Purpose |
|------|---------|
| `list_files(path)` | Recursively list files in the repo (skips `.git`) |
| `read_file(path)` | Read any file's full content |
| `write_file(path, content)` | Write/overwrite files (auto-creates parent dirs) |
| `run_shell(command)` | Run shell commands in the repo root (git, node, npm) |
| `create_plan(text)` | Persist the plan before modifications begin |
| `summarise_changes(text)` | Persist a Markdown summary after all changes are done |

---

## How the Repository Is Explored

1. `list_files('.')` gives the agent a complete file tree (`.git` excluded).
2. The agent identifies entry points (`server.js`, `package.json`) and reads them first.
3. It then reads `app/models/`, `app/controllers/`, `app/routes/` and `config/` in order.
4. After reading, the agent understands the schema (title + content), the existing CRUD routes, and what is missing.

---

## Features Implemented in the Node.js App

The agent implements the following improvements automatically:

### A — Tags
- `tags: [String]` field added to the Note Mongoose schema
- `POST /notes` and `PUT /notes/:id` accept a `tags` array in the request body
- `GET /notes/tags/:tag` — returns all notes that include the given tag

### B — Full-Text Search
- MongoDB text index created on `title` and `content` fields
- `GET /notes/search?q=<query>` — returns notes matching the search query, sorted by relevance score

### C — Pagination
- `GET /notes?page=1&limit=10` — returns a page of notes
- Response includes `{ data, total, page, limit, totalPages }` envelope

### D — Sorting
- `GET /notes?sort=createdAt&order=desc` — sort by any field in either direction

---

## Setup & Usage

### Prerequisites
- Python 3.11+
- `git` installed and on PATH
- Node.js (for syntax validation in the target repo)
- A [Gemini API key](https://aistudio.google.com/app/api-keys)

### Installation

```bash
# 1. Clone this repo
git clone <this-repo-url>
cd ai-coding-agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=<your key>

# 5. Run the agent
python agent.py
```

The agent will:
- Clone `node-easy-notes-app` into `workspace/` automatically
- Print live progress to the terminal
- Save `execution_plan.txt` and `changes_summary.txt` in the project root

---

## Outputs

| File | Description |
|------|-------------|
| `execution_plan.txt` | The plan the agent created before modifying any files |
| `changes_summary.txt` | Markdown summary of every change made |
| `workspace/node-easy-notes-app/` | The fully modified Node.js repository |

---

## Assumptions & Trade-offs

| Decision | Rationale |
|----------|-----------|
| Google Antigravity SDK | Used as specified in the assignment; provides clean tool-call loop |
| Default Gemini model | The SDK's default is used; avoids hard-coding a model that may be deprecated |
| Tags stored as `[String]` | Simplest approach compatible with existing Mongoose setup; no separate collection needed |
| MongoDB text index | Native MongoDB capability — no extra search dependency required |
| Pagination envelope wraps existing response | Non-breaking; old clients can still use `data[0]` indexing |
| `node --check` for validation | Catches syntax errors without needing a running MongoDB instance |
| Local git commit | The repo is committed locally; pushing to GitHub requires user credentials and is outside the agent's scope to avoid storing tokens |

---

## Running Without a Gemini API Key

If you want to see what the agent *would* produce without calling the LLM, the modified Node.js files are included in `workspace/node-easy-notes-app/` (after running the agent at least once).
