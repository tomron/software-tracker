## 1. Repository Scaffolding

- [x] 1.1 Create top-level directory structure: `projects/`, `data/`, `docs/docs/assets/`, `docs/data/`, `.github/workflows/`
- [x] 1.2 Initialise `pyproject.toml` with `[project]` metadata and dependencies: `PyGitHub`, `requests`, `beautifulsoup4`, `openai`, `anthropic`, `pydantic`
- [x] 1.3 Run `uv lock` to generate `uv.lock`
- [x] 1.4 Create `global-config.json` with default values and inline comments documenting every field
- [x] 1.5 Create an example project folder `projects/example/config.json` covering all optional fields as a reference template
- [x] 1.6 Add `.gitignore` entries for `__pycache__`, `.venv`, `*.pyc`

## 2. Config Loading & Validation

- [x] 2.1 Define Pydantic models in `tracker/models.py`: `GlobalConfig`, `ProjectConfig`, `LlmConfig`, `SearchConfig`, `NotifyConfig`, `AlternativeEntry`, `LinkEntry`; use `model_validator` for cross-field rules (e.g. default `api_key_env`)
- [x] 2.2 Implement `tracker/config.py`: load `global-config.json` with `GlobalConfig.model_validate()`; missing file returns `GlobalConfig()` (all defaults)
- [x] 2.3 Implement project discovery: scan `projects/*/config.json`, parse with `ProjectConfig.model_validate()`; catch `ValidationError` per project, log field-level errors and skip that project
- [x] 2.4 Implement question merging: global questions + project questions, deduplicating on exact string match
- [x] 2.5 Implement notify config resolution: project `notify` block overrides global entirely if present
- [x] 2.6 Implement `instructions` merging: global instructions prepended to project instructions
- [x] 2.7 Implement `api_key_env` resolution for LLM and search providers; raise clear error if env var unset

## 3. Data Fetching

- [x] 3.1 Implement `tracker/fetcher.py`: changelog URL inference (GitHub Releases → CHANGELOG.md → homepage scrape)
- [x] 3.2 Implement GitHub Releases fetch via PyGitHub: retrieve last 5 release bodies; fall back to `CHANGELOG.md` if bodies are empty
- [x] 3.3 Implement web scraper: fetch URL with `requests`, extract visible text with `beautifulsoup4`; handle non-200 responses with warning log
- [x] 3.4 Handle GitHub API rate limit (403/429): log error, mark project as skipped, continue to next project

## 4. LLM Summarisation & Q&A

- [x] 4.1 Implement `tracker/llm.py`: build structured prompt from changelog text, questions, and merged instructions
- [x] 4.2 Call LLM with JSON/structured output mode; parse response into `summary`, `answers`, `breaking_changes`, `breaking_excerpts`
- [x] 4.3 Implement retry on JSON parse failure (one retry); on second failure store raw text as `summary`, empty `answers`
- [x] 4.4 Support both OpenAI and Anthropic providers via the configured `provider` field and resolved API key
- [x] 4.5 Respect per-project `llm.model` override if present in project config

## 5. Alternatives Discovery

- [x] 5.1 Implement `tracker/alternatives.py`: call LLM with web-search tool (up to 3 searches) using project name and description
- [x] 5.2 Fall back to LLM training-data only (mark `source: llm_only`) when no search API key is configured
- [x] 5.3 Merge config `alternatives` entries (mark `source: config`) into LLM-discovered list
- [x] 5.4 Deduplicate: config entry takes precedence when LLM discovers a project already named in config alternatives
- [x] 5.5 Normalise output: each entry has `name`, optional `url` (first link from config if available), `review`, `source`

## 6. Output Storage

- [x] 6.1 Implement `tracker/storage.py`: rotate `latest.json` → `previous.json` before writing new output
- [x] 6.2 Write `data/<slug>/latest.json` with fields: `project_slug`, `run_at`, `summary`, `answers`, `breaking_changes`, `breaking_excerpts`, `alternatives`
- [x] 6.3 Write `docs/data/<slug>.json` with the same content as `latest.json`
- [x] 6.4 Regenerate `docs/data/index.json` from all project `config.json` files after every run (list of `{slug, name}`)

## 7. Diff & Notifications

- [x] 7.1 Implement `tracker/diff.py`: compare `latest.json` vs `previous.json`; emit `answer_changed` events for each changed answer
- [x] 7.2 Emit `breaking_change` event when `breaking_changes` flips to `true`
- [x] 7.3 Always emit `run_complete` event on successful project completion
- [x] 7.4 Emit `error` event with step name and message on any pipeline exception for a project
- [x] 7.5 Implement `tracker/notify.py`: evaluate effective `on` list; POST to each ntfy.sh topic for matching events
- [x] 7.6 Format notification bodies: answer-change lists question + old/new values; breaking-change includes excerpts; run-complete includes timestamp + one-line summary; error includes step + message
- [x] 7.7 Include `Authorization: Bearer` header when `NTFY_TOKEN` env var is set; log ntfy.sh POST failures without failing the run
- [x] 7.8 Apply error-notification fallback: use global topics when a project has no `notify` block

## 8. Pipeline Entrypoint

- [x] 8.1 Implement `tracker/__main__.py`: CLI accepting optional `--project <slug>` argument
- [x] 8.2 When `--project` is omitted, discover and run all projects; when provided, validate slug exists and run only that project
- [x] 8.3 Exit with non-zero code if the LLM API key env var is missing; otherwise complete the run and report per-project success/skip/error counts
- [x] 8.4 Validate that at least one of `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` is set before processing begins

## 9. GitHub Actions Workflow

- [x] 9.1 Create `.github/workflows/track.yml` with `schedule` trigger (weekly, Monday 08:00 UTC) and `workflow_dispatch` with optional `project` input
- [x] 9.2 Add `concurrency` group to serialise runs (cancel-in-progress: false)
- [x] 9.3 Workflow steps: checkout → install `uv` → `uv sync --frozen` → `uv run python -m tracker [--project $INPUT]`
- [x] 9.4 Validate `project` input: if non-empty and not a valid slug, print available slugs and exit with error
- [x] 9.5 After pipeline completes, commit changed files in `data/` and `docs/data/` with message `"chore: update tracker data [YYYY-MM-DD]"` using `GITHUB_TOKEN`; skip commit if no changes
- [x] 9.6 Document required secrets (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`, optional `NTFY_TOKEN`) in workflow file comments

## 10. Web UI — Structure & Data

- [x] 10.1 Create `docs/index.html` with semantic HTML skeleton: header (title + theme toggle), category filter bar, project card grid, footer
- [x] 10.2 Create `docs/assets/style.css`: CSS custom properties for light/dark palettes, system font stack, base reset
- [x] 10.3 Create `docs/assets/app.js`: fetch `docs/data/index.json`, then fetch each project JSON, render cards into the grid
- [x] 10.4 Implement hash/query routing in `app.js`: `?project=<slug>` renders detail view; no hash renders index
- [x] 10.5 Add `<noscript>` fallback message to `index.html`

## 11. Web UI — Index & Filtering

- [x] 11.1 Render project cards: name, description, category tags, last-run timestamp, breaking-change badge
- [x] 11.2 Collect all unique categories from loaded project data; render as clickable filter chips above the grid
- [x] 11.3 Implement filter logic: clicking a chip toggles it; show projects matching any active chip (OR); no chips = show all
- [x] 11.4 Visually highlight active filter chips

## 12. Web UI — Project Detail View

- [x] 12.1 Render detail view: name, description, homepage/repo links, categories, last-run timestamp, full summary
- [x] 12.2 Render Q&A answers as a table (question / answer pairs)
- [x] 12.3 Render breaking-change section: warning banner + excerpts (only when `breaking_changes: true`)
- [x] 12.4 Render alternatives list: name, review text, URL link if present; badge for source (`config` vs `discovered`)
- [x] 12.5 Add breadcrumb / back link to index

## 13. Web UI — Dark/Light Mode & Responsive Design

- [x] 13.1 Implement theme toggle button: reads `localStorage` on load, falls back to `prefers-color-scheme`; toggles `data-theme` attribute on `<html>`
- [x] 13.2 Define dark-mode CSS custom properties under `[data-theme="dark"]`; verify WCAG AA contrast ratios for both themes
- [x] 13.3 Implement responsive grid: single column below 640px, multi-column (2–4) above using CSS grid `auto-fill`
- [x] 13.4 Ensure all interactive elements (cards, chips, toggle, links) have min 44×44px touch targets
- [x] 13.5 Test layout at 320px, 640px, 1024px, and 1440px viewport widths

## 14. Docs & Example Project

- [x] 14.1 Write `README.md` with the following sections, each written in full prose with examples:
  - **What this is** — one-paragraph overview of the tool's purpose
  - **How it works** — brief description of the pipeline (fetch → LLM → diff → notify → GitHub Pages)
  - **Prerequisites** — Python 3.11+, uv, a GitHub repo with Pages enabled, LLM API key
  - **Quick start** — step-by-step: fork/clone repo, configure secrets, enable GitHub Pages, add first project, trigger first run
  - **Adding a project** — how to create `projects/<slug>/config.json`; full annotated example showing every field with explanation; note that only `name` is required
  - **Global configuration** — full annotated `global-config.json` example; explanation of every field including `llm`, `search`, `notify`, `questions`, `instructions`
  - **Configuring notifications (ntfy.sh)** — how to set up a topic, available event types (`answer_changed`, `breaking_change`, `run_complete`, `error`), per-project override vs global
  - **GitHub Actions setup** — list of required and optional secrets (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, `NTFY_TOKEN`), how to set them in repo settings; how to trigger a scheduled vs manual run; how to run for a single project via `workflow_dispatch`
  - **Running locally** — `uv sync`, `uv run python -m tracker`, `uv run python -m tracker --project <slug>`
  - **Dashboard (GitHub Pages)** — how to enable Pages on the repo (`docs/` folder, main branch), URL where it will be served, description of index and project detail views
  - **Project config reference** — complete field-by-field table for `config.json` (field name, type, required, default, description)
  - **Global config reference** — same table for `global-config.json`
  - **Troubleshooting** — common issues: missing API key error, ntfy.sh not receiving notifications, GitHub rate limit, validation errors in config
- [x] 14.2 Add a second example tracked project (e.g. `projects/keycloak/config.json`) with realistic questions and alternatives to exercise the full pipeline
