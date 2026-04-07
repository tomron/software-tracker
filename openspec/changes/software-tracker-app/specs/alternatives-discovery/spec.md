## ADDED Requirements

### Requirement: LLM-driven alternatives discovery with web search
For each project, the pipeline SHALL invoke the LLM with a web-search tool to discover and briefly review alternative projects. This step runs as part of the same pipeline run, after changelog fetching.

#### Scenario: Alternatives discovered via web search
- **WHEN** the project has a `name` and `description` (or inferred description from changelog)
- **THEN** the pipeline calls the LLM with the project name, description, and a web-search tool; the LLM performs up to 3 searches and returns a list of alternatives

#### Scenario: Web search tool unavailable
- **WHEN** the configured LLM provider does not support a native web-search tool and no `SEARCH_API_KEY` is configured
- **THEN** the pipeline skips web search and asks the LLM for alternatives from its training data only, marking results with `"source": "llm_only"`

---

### Requirement: Alternatives output structure
Each discovered alternative SHALL be returned as a structured object with `name` (required), `url` (optional), and `review` (one-sentence description of trade-offs, required).

#### Scenario: Alternative with all fields
- **WHEN** the LLM returns a complete alternative entry
- **THEN** the entry is stored as `{ "name": "...", "url": "...", "review": "...", "source": "web_search" }`

#### Scenario: LLM returns no alternatives
- **WHEN** the LLM finds no meaningful alternatives
- **THEN** the `alternatives` field in the output is an empty list, not an error

---

### Requirement: Alternatives from config inform discovery
If the project `config.json` includes a `alternatives` list, those entries SHALL be included in the alternatives output alongside any LLM-discovered ones, marked with `"source": "config"`.

#### Scenario: Configured alternative merged into output
- **WHEN** `alternatives` contains `{ "name": "Auth0", "links": ["https://auth0.com"], "comment": "SaaS-only" }`
- **THEN** the output includes `{ "name": "Auth0", "url": "https://auth0.com", "review": "SaaS-only", "source": "config" }`

#### Scenario: LLM discovers project already in config alternatives list
- **WHEN** the LLM suggests a project whose name matches an entry already in the config's alternatives list
- **THEN** the config entry takes precedence and the LLM entry is deduplicated
