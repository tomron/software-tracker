## ADDED Requirements

### Requirement: Fetch changelog content from GitHub
For projects with a GitHub `repo` URL, the pipeline SHALL fetch release notes via the GitHub Releases API. If fewer than 3 releases exist or releases have no bodies, the pipeline SHALL fall back to fetching `CHANGELOG.md` from the default branch.

#### Scenario: GitHub releases available
- **WHEN** the repo has at least one GitHub Release with a non-empty body
- **THEN** the pipeline retrieves the bodies of the last 5 releases (or all if fewer)

#### Scenario: Releases have no body text
- **WHEN** GitHub releases exist but all have empty bodies
- **THEN** the pipeline fetches `CHANGELOG.md` from the repo's default branch

#### Scenario: GitHub API rate limit hit
- **WHEN** the GitHub API returns a 403 or 429 rate-limit response
- **THEN** the pipeline logs the error, skips the project, and does not fail the entire run

---

### Requirement: Fetch changelog content via web scraping
For projects with a `changelog_url` (explicit or inferred homepage), the pipeline SHALL fetch the page and extract visible text using an HTML parser. JavaScript-rendered content is not required.

#### Scenario: Changelog page fetched successfully
- **WHEN** the `changelog_url` returns a 200 response
- **THEN** the pipeline extracts all visible text content from the page body

#### Scenario: Changelog page returns error
- **WHEN** the `changelog_url` returns a non-200 HTTP status
- **THEN** the pipeline logs a warning and proceeds with empty changelog content for that project

---

### Requirement: LLM-based summarization and Q&A
The pipeline SHALL send fetched changelog content to an LLM in a single call per project. The LLM SHALL return a structured JSON response containing a summary, answers to all configured questions, and a breaking-change assessment.

#### Scenario: LLM call with questions
- **WHEN** changelog content and a list of questions are available
- **THEN** the pipeline sends a single prompt containing the changelog text and all questions, and receives a JSON response with fields: `summary`, `answers` (object keyed by question text), `breaking_changes` (boolean), `breaking_excerpts` (list of strings)

#### Scenario: LLM returns unexpected format
- **WHEN** the LLM response cannot be parsed as valid JSON
- **THEN** the pipeline retries once; if still invalid, logs an error and stores raw text as `summary` with empty `answers`

#### Scenario: No questions configured
- **WHEN** neither the project config nor global config define any questions
- **THEN** the pipeline still calls the LLM for a summary and breaking-change detection, with an empty `answers` object

---

### Requirement: Pipeline output stored as JSON
After processing, the pipeline SHALL write the result to `data/<project-slug>/latest.json`. Before writing, it SHALL copy any existing `latest.json` to `previous.json`.

#### Scenario: First run for a project
- **WHEN** no `latest.json` exists for a project
- **THEN** the pipeline writes `latest.json` and does not create `previous.json`

#### Scenario: Subsequent run
- **WHEN** `latest.json` already exists
- **THEN** it is renamed to `previous.json` before the new `latest.json` is written

#### Scenario: Output JSON structure
- **WHEN** a run completes successfully
- **THEN** `latest.json` contains: `project_slug`, `run_at` (ISO 8601 timestamp), `summary`, `answers`, `breaking_changes`, `breaking_excerpts`, `alternatives` (from the alternatives-discovery step)
