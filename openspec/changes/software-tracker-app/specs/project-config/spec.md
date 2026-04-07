## ADDED Requirements

### Requirement: Project folder structure
Each tracked project SHALL be represented as a folder under `projects/<project-slug>/` containing a `config.json` file. The presence of this folder is sufficient to register the project with the tracker.

#### Scenario: New project detected
- **WHEN** a folder exists at `projects/<slug>/config.json`
- **THEN** the tracker pipeline includes that project in its next run

#### Scenario: Missing config.json ignored
- **WHEN** a folder exists under `projects/` but contains no `config.json`
- **THEN** the pipeline skips that folder and logs a warning

---

### Requirement: Project config.json schema
Each `projects/<slug>/config.json` file SHALL conform to the following schema. Only `name` is required; all other fields are optional.

```
{
  "name": string,                  // required — display name
  "description": string,           // short description
  "repo": string,                  // GitHub or other repo URL
  "homepage": string,              // official website URL
  "changelog_url": string,         // explicit changelog URL; inferred if absent
  "links": [                       // supplementary URLs
    { "label": string, "url": string }
  ],
  "categories": [string],          // grouping tags for the UI
  "questions": [string],           // plain list of question strings
  "alternatives": [
    {
      "name": string,              // required
      "links": [string],           // optional URLs
      "comment": string            // optional free-text note
    }
  ],
  "notify": {                      // overrides global notify if present
    "topics": [string],
    "on": [string]                 // e.g. ["answer_changed", "breaking_change"]
  }
}
```

#### Scenario: Valid minimal config accepted
- **WHEN** `config.json` contains only `{ "name": "Keycloak" }`
- **THEN** the pipeline processes the project using all global defaults

#### Scenario: Invalid JSON rejected
- **WHEN** `config.json` contains malformed JSON
- **THEN** the pipeline skips that project and logs an error with the file path

#### Scenario: Schema validation failure logged with field path
- **WHEN** `config.json` is valid JSON but fails Pydantic model validation (e.g. missing `name`, wrong field type)
- **THEN** the pipeline skips that project and logs the Pydantic `ValidationError` including the exact field path (e.g. `alternatives[0].name`)

---

### Requirement: Global config.json schema
A `global-config.json` file at the repository root SHALL define defaults applied to all projects. All fields are optional.

```
{
  "llm": {
    "provider": string,        // "openai" or "anthropic"
    "model": string,           // e.g. "gpt-4o-mini"
    "api_key_env": string      // env var name holding the API key; default "OPENAI_API_KEY" or "ANTHROPIC_API_KEY"
  },
  "search": {
    "provider": string,        // e.g. "brave", "serper"
    "api_key_env": string      // env var name holding the search API key; default "SEARCH_API_KEY"
  },
  "notify": {
    "topics": [string],
    "on": [string]
  },
  "questions": [string],       // applied to every project
  "instructions": string       // global system prompt / general instructions injected into every LLM call
}
```

`api_key_env` specifies the **name** of the environment variable to read at runtime — the key itself is never stored in the config file.

#### Scenario: Global questions merged with project questions
- **WHEN** `global-config.json` defines `questions: ["What is the license?"]` and a project config defines `questions: ["Supports Okta?"]`
- **THEN** the pipeline asks both questions for that project

#### Scenario: Project notify overrides global notify
- **WHEN** a project `config.json` contains a `notify` block
- **THEN** that block is used in full for that project and the global notify block is ignored for it

#### Scenario: No global-config.json present
- **WHEN** `global-config.json` does not exist
- **THEN** the pipeline proceeds using built-in defaults (openai / gpt-4o-mini, no global questions, no notifications)

#### Scenario: Custom api_key_env for LLM
- **WHEN** `llm.api_key_env` is set to `"MY_LLM_KEY"`
- **THEN** the pipeline reads the API key from the `MY_LLM_KEY` environment variable instead of the default

#### Scenario: API key env var not set
- **WHEN** the resolved env var for the LLM or search provider is empty or unset
- **THEN** the pipeline fails with a clear error naming the missing env var

---

### Requirement: Per-project LLM instructions
A project `config.json` MAY include an `instructions` field containing a free-text string that is appended to the global instructions (if any) and injected as additional context into every LLM call for that project.

```
{
  "name": "Keycloak",
  ...
  "instructions": "Focus on enterprise features, SSO support, and Kubernetes deployment options."
}
```

#### Scenario: Project instructions merged with global instructions
- **WHEN** `global-config.json` defines `instructions: "Be concise."` and a project config defines `instructions: "Focus on enterprise features."`
- **THEN** the LLM prompt receives both, with the global instructions first and project instructions appended

#### Scenario: Instructions present in project config only
- **WHEN** only the project config defines `instructions`
- **THEN** only the project instructions are injected; no global instructions are prepended

#### Scenario: No instructions defined anywhere
- **WHEN** neither global nor project config defines `instructions`
- **THEN** the LLM is called with no additional system-prompt context beyond the built-in prompt template

---

### Requirement: Changelog URL inference
If `changelog_url` is absent from the project config, the pipeline SHALL attempt to infer the changelog source in this priority order:
1. GitHub Releases API (if `repo` is a GitHub URL)
2. `CHANGELOG.md` or `CHANGELOG` file in the default branch of the repo
3. Homepage URL (scrape visible text)

#### Scenario: GitHub repo without explicit changelog_url
- **WHEN** `repo` is a GitHub URL and `changelog_url` is absent
- **THEN** the pipeline fetches data via GitHub Releases API

#### Scenario: No repo URL and no changelog_url
- **WHEN** neither `repo` nor `changelog_url` is set but `homepage` is set
- **THEN** the pipeline scrapes the homepage URL

#### Scenario: No URLs at all
- **WHEN** `repo`, `homepage`, and `changelog_url` are all absent
- **THEN** the pipeline skips the data-fetch step for that project and logs a warning
