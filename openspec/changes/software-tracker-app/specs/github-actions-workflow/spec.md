## ADDED Requirements

### Requirement: Scheduled pipeline run
The GitHub Actions workflow SHALL run on a configurable schedule (default: weekly on Monday at 08:00 UTC) to process all tracked projects.

#### Scenario: Scheduled run processes all projects
- **WHEN** the scheduled trigger fires
- **THEN** the workflow runs the pipeline for every folder under `projects/` and commits any changes to `data/` and `docs/data/`

#### Scenario: No changes after run
- **WHEN** the pipeline completes but produces no file changes
- **THEN** the workflow skips the commit step and exits cleanly

---

### Requirement: Manual dispatch — all projects or single project
The workflow SHALL support `workflow_dispatch` with an optional `project` input. If `project` is blank or omitted, all projects are processed. If a project slug is provided, only that project is processed.

#### Scenario: Manual run for all projects
- **WHEN** the workflow is dispatched with `project` left blank
- **THEN** the pipeline runs for every project under `projects/`

#### Scenario: Manual run for a single project
- **WHEN** the workflow is dispatched with `project: keycloak`
- **THEN** the pipeline runs only for `projects/keycloak/` and updates only `data/keycloak/` and `docs/data/keycloak.json`

#### Scenario: Invalid project slug provided
- **WHEN** the workflow is dispatched with a `project` value that does not match any folder under `projects/`
- **THEN** the workflow exits with an error message listing available project slugs

---

### Requirement: Python environment with uv
The workflow SHALL install Python dependencies using `uv`. It SHALL run `uv sync` to install from `uv.lock` and execute the pipeline with `uv run`.

#### Scenario: Dependencies installed via uv
- **WHEN** the workflow job starts
- **THEN** it installs `uv`, runs `uv sync --frozen`, and invokes the pipeline via `uv run python -m tracker`

---

### Requirement: Commit and push results
After a successful pipeline run the workflow SHALL commit any changed files in `data/` and `docs/data/` to the main branch using the built-in `GITHUB_TOKEN`.

#### Scenario: Results committed after run
- **WHEN** the pipeline produces file changes
- **THEN** the workflow commits with message `"chore: update tracker data [<date>]"` and pushes to the default branch

#### Scenario: Workflow concurrency guard
- **WHEN** a new workflow run is triggered while a previous run is still in progress
- **THEN** the new run is queued and the in-progress run is allowed to finish before it starts (using a `concurrency` group)

---

### Requirement: Required secrets
The workflow SHALL document and use the following GitHub Actions secrets: `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` (depending on configured provider), `NTFY_TOKEN` (optional), and the built-in `GITHUB_TOKEN`.

#### Scenario: Missing LLM API key
- **WHEN** neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is set as a secret
- **THEN** the pipeline fails with a clear error message indicating which secret is missing

#### Scenario: Missing NTFY_TOKEN
- **WHEN** `NTFY_TOKEN` is not set but notifications are configured
- **THEN** the pipeline sends unauthenticated requests to ntfy.sh (valid for public topics)
