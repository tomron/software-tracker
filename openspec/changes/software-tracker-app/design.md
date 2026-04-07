## Context

This is a greenfield personal-use tool: a GitHub repository that doubles as both the data store and the hosting platform. There is no existing codebase to integrate with. The system must run unattended on GitHub Actions (free tier), write results back to the repo, and serve a dashboard via GitHub Pages — all with zero separate infrastructure.

Key constraints:
- No paid hosting; GitHub Actions minutes and GitHub Pages are the compute and serving layer
- LLM API calls cost money: minimize tokens by working from changelogs/release notes, not full repo diffs
- The user wants to add new projects with minimal friction (drop a folder in, done)
- Python dependency management via `uv`

## Goals / Non-Goals

**Goals:**
- File-based project registry — add a folder, get tracking
- Periodic pipeline: fetch → summarize → answer questions → discover alternatives → diff → notify
- Structured JSON output per project stored in the repo, versioned automatically
- ntfy.sh notifications on meaningful changes only (answer flips, breaking changes)
- GitHub Pages dashboard: lightweight, no build step, readable without JS

**Non-Goals:**
- Real-time or webhook-driven updates (scheduled/manual only)
- Multi-user or auth-gated UI
- Tracking private repositories
- Fine-grained commit-level diffing (release notes and changelogs are the unit)
- Self-hosted LLM (always calls an external API)

## Decisions

### 1. Config file schema

**Format:** JSON (single `config.json` per project folder).

**Project config** (`projects/<name>/config.json`):
```json
{
  "name": "Keycloak",
  "description": "Open source identity and access management",
  "repo": "https://github.com/keycloak/keycloak",
  "homepage": "https://www.keycloak.org",
  "changelog_url": "https://www.keycloak.org/docs/latest/release_notes/",
  "links": [
    { "label": "Blog", "url": "https://www.keycloak.org/blog" }
  ],
  "categories": ["auth", "identity"],
  "questions": [
    "Does it support Okta as an identity provider?",
    "What is the current license?",
    "Is there an official hosted/cloud version?"
  ],
  "alternatives": [
    {
      "name": "Auth0",
      "links": ["https://auth0.com"],
      "comment": "SaaS-only, generous free tier"
    },
    { "name": "Authentik" }
  ],
  "notify": {
    "topics": ["my-tracker-keycloak"],
    "on": ["answer_changed", "breaking_change"]
  }
}
```

**Global config** (`global-config.json`):
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "search": {
    "provider": "brave"
  },
  "notify": {
    "topics": ["my-tracker"],
    "on": ["answer_changed", "breaking_change"]
  },
  "questions": [
    "What is the current license?",
    "Is the project actively maintained?"
  ]
}
```

Rules:
- `changelog_url` is optional; if absent the pipeline infers it (GitHub releases → `CHANGELOG.md` → homepage scrape)
- `questions` in a project config are **merged** with global questions (project questions take precedence on duplicates)
- `notify` in a project config **overrides** the global notify block entirely if present
- `alternatives[].name` is the only required field; `links` and `comment` are optional
- `links` is a list of `{ label, url }` objects for any supplementary URLs

### 2. Repository layout

```
projects/
  <project-name>/
    config.json         # metadata, questions, alternatives, notify overrides
data/
  <project-name>/
    latest.json         # most recent pipeline output
    previous.json       # previous run (for diff)
docs/
  index.html            # GitHub Pages dashboard entry point
  assets/               # CSS, JS
global-config.json      # default questions, notify rules, LLM provider
pyproject.toml          # Python deps managed by uv
.github/workflows/
  track.yml             # scheduled + manual dispatch workflow
```

**Why this over a database:** The repo IS the database. GitHub Actions commits results, git history is the audit trail, GitHub Pages serves the UI — zero extra infrastructure.

### 2. Python tooling: uv

Use `uv` for all dependency management: `pyproject.toml` declares deps, `uv.lock` pins them, `uv sync` installs in CI, `uv run` executes scripts.

**Why uv over pip/poetry:** Faster installs in CI, single tool for venv + lock + run, first-class `pyproject.toml` support.

### 3. Config validation: Pydantic

All config files (`global-config.json` and per-project `config.json`) are parsed and validated using Pydantic v2 models defined in `tracker/models.py`. Key models: `GlobalConfig`, `ProjectConfig`, `LlmConfig`, `SearchConfig`, `NotifyConfig`, `AlternativeEntry`, `LinkEntry`.

Benefits:
- Field-level validation errors with exact path (e.g. `alternatives[0].name` missing)
- Default values declared in the model, not scattered across loading code
- `model_validator` handles cross-field logic (e.g. inferring default `api_key_env` from `provider`)
- Models double as typed data structures throughout the pipeline, eliminating dict key typos

`ValidationError` is caught per-project during discovery; the offending project is skipped with a structured log message and the run continues.

### 3. Data fetching strategy

**GitHub-hosted projects:** Use the GitHub REST API (via `PyGitHub`) to fetch releases and their bodies. Fall back to `CHANGELOG.md` or `CHANGELOG` in the default branch if releases are sparse.

**Non-GitHub / commercial projects:** Scrape the project's changelog URL defined in `config.yml` using `requests` + `beautifulsoup4`. Extract visible text from the page; pass to LLM.

**Why not RSS:** Many projects don't publish RSS feeds; scraping is more universal. RSS can be added as an optional fetch mode per project.

### 4. LLM usage

A single LLM call per project per run with a structured prompt:
- Input: concatenated changelog/release text (trimmed to last N releases or last 6 months)
- Output: JSON with `summary`, `answers` (one per configured question), `breaking_changes` (bool + excerpts), `alternatives_review` (if enabled)

Use structured output / JSON mode to avoid parsing fragility.

**Provider:** configurable in `global-config.json` (`openai` or `anthropic`). Default model: `gpt-4o-mini` / `claude-haiku` for cost efficiency; overridable per project.

**Why one call:** Minimizes latency, cost, and complexity. All questions answered in a single pass over the same context window.

### 5. Alternatives discovery

Include a `web_search` tool call in the LLM prompt (via OpenAI function calling or Anthropic tool use) to let the model search for alternatives. The model receives the project name and description, performs up to 3 searches, and returns a short list of alternatives with a one-line review each.

**Why LLM + web search over GitHub topic search:** More nuanced — can find non-GitHub alternatives, SaaS competitors, and explain trade-offs in plain language.

### 6. Diff and notification logic

After each run, `latest.json` is compared to `previous.json` (the prior run's output). The diff checks:
- Any answer changed value (e.g. `"no" → "yes"` for a question)
- `breaking_changes` flipped to `true`
- New alternatives added

Notification rules are evaluated in priority order: per-project `config.yml` overrides `global-config.json`. Each rule specifies which diff events trigger a notification and to which ntfy.sh topic.

**Why ntfy.sh:** Zero-infrastructure push notifications; free tier is sufficient for personal use. Simple HTTP POST.

### 7. GitHub Pages UI

Pure HTML + vanilla JS — no build step, no framework. Actions writes `docs/data/<project>.json` alongside `docs/index.html`. The page fetches project JSON files at runtime and renders them client-side.

**Why no framework/SSG:** Eliminates a build step in Actions, keeps the repo simple, loads fast, works without JS for the static parts.

### 8. GitHub Actions workflow

Single workflow file `track.yml` with:
- `schedule` trigger (e.g. weekly, configurable via workflow input)
- `workflow_dispatch` trigger with optional `project` input (blank = all projects)

The job: checkout → `uv sync` → `uv run python -m tracker [--project <name>]` → commit updated `data/` and `docs/data/` → push.

**Why write back to repo in the same job:** Keeps the pipeline self-contained. The committed JSON is the source of truth for the UI and for future diffs.

## Risks / Trade-offs

- **LLM cost creep** → Mitigation: use cheap models by default (`gpt-4o-mini`/`claude-haiku`), cap input tokens per project, allow disabling LLM per project
- **GitHub Actions push conflicts** (concurrent runs overwriting each other) → Mitigation: the workflow uses `concurrency` group to serialize runs; manual runs queue behind scheduled ones
- **Scraping brittleness** (page structure changes) → Mitigation: scraper extracts all visible text rather than targeting specific DOM elements; LLM handles noisy input gracefully
- **GitHub API rate limits** (60 req/hr unauthenticated, 5000 with token) → Mitigation: always use `GITHUB_TOKEN`; fetch only release objects, not commits
- **ntfy.sh topic is public by default** → Mitigation: document that users should use a hard-to-guess topic name or enable ntfy.sh access tokens

## Open Questions

- Should the dashboard show a full answer history timeline, or just current + previous? (Start with current + previous; history is available via git log)
- Web search API for alternatives: use OpenAI's built-in search tool, Anthropic's web search tool, or a separate Serper/Brave API key? (Decision: use the LLM provider's native search tool if available; fall back to a configurable `SEARCH_API_KEY` for Brave/Serper)
