# Software Tracker

Software Tracker is a GitHub-native tool that periodically monitors open source and commercial software projects, summarises their changes, answers predefined questions about each project (e.g. "Does it support Okta?"), discovers alternatives, and sends notifications when something important changes. Everything runs inside your GitHub repository: GitHub Actions fetches and analyses data, results are committed back to the repo, and a lightweight dashboard is served via GitHub Pages — no separate infrastructure required.

---

## How it works

Each run follows this pipeline for every tracked project:

1. **Fetch** — pull release notes from the GitHub Releases API, fall back to `CHANGELOG.md`, or scrape the project's changelog URL.
2. **Analyse** — send the fetched text to an LLM (OpenAI or Anthropic) in a single call. The model returns a summary, answers to your configured questions, and a breaking-change assessment.
3. **Discover alternatives** — the LLM uses a web-search tool (if a search API key is configured) or its training data to suggest alternative projects, supplemented by any alternatives you have listed in the project config.
4. **Store** — write `data/<slug>/latest.json` (and rotate the previous one to `previous.json`), then copy the result to `docs/data/<slug>.json` for the dashboard.
5. **Diff** — compare the new output against the previous run to detect answer flips and new breaking changes.
6. **Notify** — send push notifications via [ntfy.sh](https://ntfy.sh) for configured event types.
7. **Dashboard** — GitHub Pages serves `docs/index.html`, which fetches the JSON files at runtime to render a project index and per-project detail pages.

---

## Prerequisites

- A GitHub repository (fork this repo or use it as a template)
- Python 3.11 or newer (only needed for running locally)
- [uv](https://docs.astral.sh/uv/) for local Python dependency management
- An LLM API key: either **OpenAI** (`OPENAI_API_KEY`) or **Anthropic** (`ANTHROPIC_API_KEY`)
- Optional: a [Brave Search](https://brave.com/search/api/) or [Serper](https://serper.dev) API key for alternatives web search

---

## Quick start

1. **Fork or clone** this repository.

2. **Add your LLM API key** as a GitHub Actions secret:
   - Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   - Add `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY` if you prefer Anthropic)

3. **Enable GitHub Pages**:
   - Go to your repo → **Settings** → **Pages**
   - Under *Source*, select **Deploy from a branch**, branch `main`, folder `/docs`
   - Click **Save**. Your dashboard will be available at `https://<your-username>.github.io/<repo-name>/`

4. **Add your first project** — see [Adding a project](#adding-a-project) below.

5. **Trigger the first run**:
   - Go to **Actions** → **Track projects** → **Run workflow**
   - Leave "Project slug" blank to run all projects, or enter a specific slug
   - Click **Run workflow**

---

## Adding a project

To track a new project, create a folder under `projects/` with a `config.json` file:

```
projects/
  my-project/
    config.json
```

The folder name (`my-project`) becomes the project's **slug** — it must be unique and URL-safe (lowercase, hyphens only).

Only the `name` field is required. Here is a fully annotated example covering every available field:

```json
{
  "name": "Keycloak",
  "description": "Open source identity and access management.",

  "repo": "https://github.com/keycloak/keycloak",
  "homepage": "https://www.keycloak.org",
  "changelog_url": "https://www.keycloak.org/docs/latest/release_notes/",

  "links": [
    { "label": "Blog", "url": "https://www.keycloak.org/blog" },
    { "label": "Docs", "url": "https://www.keycloak.org/documentation" }
  ],

  "categories": ["auth", "identity"],

  "questions": [
    "Does it support Okta as an identity provider?",
    "Is there an official hosted/cloud version?",
    "What is the current license?"
  ],

  "instructions": "Focus on enterprise features, SSO support, and Kubernetes deployment options.",

  "alternatives": [
    {
      "name": "Auth0",
      "links": ["https://auth0.com"],
      "comment": "SaaS-only, generous free tier."
    },
    { "name": "Authentik" }
  ],

  "notify": {
    "topics": ["my-tracker-keycloak"],
    "on": ["answer_changed", "breaking_change", "error"]
  }
}
```

**Field notes:**
- `changelog_url` is optional — if omitted the pipeline infers it from `repo` (GitHub Releases → `CHANGELOG.md`) then falls back to `homepage`.
- `questions` are merged with any global questions from `global-config.json`. Duplicates are deduplicated.
- `instructions` is appended to the global instructions (if any) and injected into every LLM call for this project.
- `alternatives[].name` is the only required field in each alternative entry.
- `notify` overrides the global notify config entirely for this project. Remove the block to inherit global settings.
- `llm` (optional) lets you override the LLM provider/model for this project specifically:
  ```json
  "llm": { "provider": "anthropic", "model": "claude-opus-4-6" }
  ```

---

## Global configuration

`global-config.json` at the repository root sets defaults applied to every project. All fields are optional. Here is a fully annotated example:

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "api_key_env": "OPENAI_API_KEY"
  },

  "search": {
    "provider": "brave",
    "api_key_env": "SEARCH_API_KEY"
  },

  "notify": {
    "topics": ["my-software-tracker"],
    "on": ["answer_changed", "breaking_change", "error"]
  },

  "questions": [
    "What is the current license?",
    "Is the project actively maintained?"
  ],

  "instructions": "Be concise. Focus on changes relevant to software engineers."
}
```

**Field notes:**
- `llm.provider`: `"openai"` or `"anthropic"`. Default: `"openai"`.
- `llm.model`: the model name to use. Default: `"gpt-4o-mini"`.
- `llm.api_key_env`: name of the environment variable holding the API key. Default: `"OPENAI_API_KEY"` or `"ANTHROPIC_API_KEY"` depending on provider.
- `search.provider`: `"brave"` or `"serper"`. Used for alternatives discovery.
- `search.api_key_env`: env var name for the search API key. Default: `"SEARCH_API_KEY"`. If not set, the LLM will answer from training data only.
- `notify.topics`: list of ntfy.sh topic names to send notifications to.
- `notify.on`: list of event types that trigger notifications (see below).
- `questions`: applied to every project, merged with per-project questions.
- `instructions`: system-level guidance injected into every LLM call.

---

## Configuring notifications (ntfy.sh)

[ntfy.sh](https://ntfy.sh) is a free, zero-setup push notification service. Notifications are sent by POSTing to a topic URL.

### Setting up a topic

A topic is just a name — anyone who knows it can subscribe. Use a hard-to-guess name or enable access tokens for privacy.

To receive notifications:
1. Install the [ntfy app](https://ntfy.sh/#subscribe) on your phone or browser.
2. Subscribe to the topic name you configure (e.g. `my-software-tracker`).

### Available event types

Set these in the `on` array of any `notify` block:

| Event | When it fires |
|---|---|
| `answer_changed` | An answer to a tracked question changed between runs |
| `breaking_change` | Breaking/deprecated/removed changes newly detected in release notes |
| `run_complete` | The pipeline completed successfully (fires every run — useful as a heartbeat) |
| `error` | The pipeline encountered an error processing a project |

### Per-project override

Add a `notify` block to a project's `config.json` to override the global settings entirely for that project:

```json
"notify": {
  "topics": ["my-tracker-keycloak"],
  "on": ["answer_changed", "breaking_change", "run_complete", "error"]
}
```

Remove the `notify` block to inherit global settings.

### Using an access token

If your ntfy.sh topic requires authentication, set the `NTFY_TOKEN` secret in GitHub Actions. The pipeline will include it as a `Bearer` token on all requests.

---

## GitHub Actions setup

### Required secrets

Go to **Settings** → **Secrets and variables** → **Actions** and add:

| Secret | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (if using OpenAI) | OpenAI API key |
| `ANTHROPIC_API_KEY` | Yes (if using Anthropic) | Anthropic API key |
| `NTFY_TOKEN` | No | ntfy.sh access token for private topics |
| `SEARCH_API_KEY` | No | Brave or Serper API key for web search during alternatives discovery |

At least one of `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` must be set, matching the `llm.provider` in `global-config.json`.

### Scheduled runs

The workflow runs automatically every **Monday at 08:00 UTC**. To change the schedule, edit the `cron` value in `.github/workflows/track.yml`.

### Manual runs

Go to **Actions** → **Track projects** → **Run workflow**:
- Leave the **Project slug** field blank to run all projects.
- Enter a slug (e.g. `keycloak`) to run only that project.

After a successful run, the workflow commits updated JSON files to `data/` and `docs/data/` and pushes to `main`.

---

## Running locally

Install dependencies:

```bash
uv sync
```

Run the full pipeline (all projects):

```bash
OPENAI_API_KEY=sk-... uv run python -m tracker
```

Run for a single project:

```bash
OPENAI_API_KEY=sk-... uv run python -m tracker --project keycloak
```

The pipeline reads `global-config.json` and all folders under `projects/`, writes to `data/` and `docs/data/`, and logs progress to stdout.

---

## Dashboard (GitHub Pages)

Once GitHub Pages is enabled (see Quick start), the dashboard is served at:

```
https://<your-username>.github.io/<repo-name>/
```

The dashboard has two views:

- **Index** — a card grid of all tracked projects. Each card shows the project name, description, category tags, last-updated timestamp, and a warning badge if breaking changes were detected. Click any card to view the full project details. Filter by category using the chips above the grid.
- **Detail** — full project view with summary, Q&A answer table, breaking-change excerpts, and alternatives list. Use the breadcrumb to return to the index.

The dashboard supports **dark and light mode** — it defaults to your OS preference and remembers your manual toggle in `localStorage`.

---

## Project config reference

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | **Yes** | — | Display name shown in the dashboard |
| `description` | string | No | `""` | Short description of the project |
| `repo` | string | No | `""` | GitHub or other repository URL |
| `homepage` | string | No | `""` | Official website URL |
| `changelog_url` | string | No | inferred | Explicit changelog URL; inferred if absent |
| `links` | array of `{label, url}` | No | `[]` | Supplementary links shown in the detail view |
| `categories` | array of strings | No | `[]` | Category tags for grouping and filtering in the UI |
| `questions` | array of strings | No | `[]` | Questions the LLM will answer; merged with global questions |
| `instructions` | string | No | `""` | Additional LLM guidance for this project; appended to global instructions |
| `alternatives` | array | No | `[]` | Known alternatives; merged with LLM-discovered ones. Each entry: `name` (required), `links` (optional), `comment` (optional) |
| `notify` | object | No | global | Notification config for this project. Overrides global entirely if present. Fields: `topics` (array of strings), `on` (array of event types) |
| `llm` | object | No | global | LLM override for this project. Fields: `provider`, `model`, `api_key_env` |

---

## Global config reference

| Field | Type | Default | Description |
|---|---|---|---|
| `llm.provider` | string | `"openai"` | LLM provider: `"openai"` or `"anthropic"` |
| `llm.model` | string | `"gpt-4o-mini"` | Model name |
| `llm.api_key_env` | string | `"OPENAI_API_KEY"` / `"ANTHROPIC_API_KEY"` | Env var name holding the API key |
| `search.provider` | string | `"brave"` | Search provider: `"brave"` or `"serper"` |
| `search.api_key_env` | string | `"SEARCH_API_KEY"` | Env var name holding the search API key |
| `notify.topics` | array of strings | `[]` | Default ntfy.sh topic names |
| `notify.on` | array of strings | `[]` | Default event types that trigger notifications |
| `questions` | array of strings | `[]` | Questions applied to every project |
| `instructions` | string | `""` | Global system-level LLM guidance |

---

## Troubleshooting

**"LLM API key env var 'OPENAI_API_KEY' is not set."**
The pipeline checks for the API key before processing any projects. Make sure the secret is set in GitHub Actions and matches the `llm.api_key_env` value in `global-config.json` (default: `OPENAI_API_KEY`).

**Not receiving ntfy.sh notifications**
- Verify the topic name in your config matches exactly what you subscribed to in the ntfy app.
- Check that the event type (e.g. `"answer_changed"`) is included in the `on` list.
- If using a private topic with access control, ensure the `NTFY_TOKEN` secret is set.
- ntfy.sh POST failures are logged but don't fail the run — check the Actions logs for warnings starting with `ntfy.sh POST`.

**GitHub API rate limit errors**
The workflow uses the built-in `GITHUB_TOKEN` which allows 5,000 requests per hour. If you are tracking many GitHub projects, rate limits should not be a problem. If you see rate limit errors, check the Actions log — the affected project is skipped and the rest of the run continues.

**"config.json failed validation"**
The pipeline logs the exact Pydantic field path that failed (e.g. `alternatives[0].name`). Open the `config.json` for that project, fix the field, and re-run. Common mistakes: missing `name` field, using an array where a string is expected, or a typo in the `notify.on` event type.

**Dashboard shows "Could not load project index"**
Run the pipeline at least once (manually via **Actions** → **Track projects** → **Run workflow**). The `docs/data/index.json` file is created on the first run. Also ensure GitHub Pages is enabled and pointing to the `docs/` folder on the `main` branch.

**No changes committed after a run**
If the pipeline finds nothing new, it skips the commit step — this is expected. Check the Actions log for per-project status (success/skipped/error counts).
