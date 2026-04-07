## Why

Keeping up with open source and commercial software projects is time-consuming: releases, breaking changes, license shifts, and feature additions are scattered across changelogs, GitHub releases, and websites. This app centralizes periodic tracking, answers predefined questions about each project (e.g. "supports Okta auth?"), and proactively notifies when something important changes.

## What Changes

- Introduce a file-based project registry: each tracked project lives in its own folder with metadata config files
- Add a Python data-pipeline that runs on a schedule (GitHub Actions) to fetch changelogs and release notes via GitHub API and web scraping
- Use an LLM (OpenAI/Anthropic) to summarize changes and answer predefined per-project questions from the fetched content
- Discover and review alternatives for each project using LLM + web search
- Diff current answers/summaries against the previous run; trigger ntfy.sh notifications for important changes (answer flips, breaking changes)
- Serve a static HTML/JS dashboard on GitHub Pages displaying per-project status, Q&A answers, summaries, and alternatives
- GitHub Actions workflow supports scheduled full runs and manual dispatch targeting all projects or a single project

## Capabilities

### New Capabilities

- `project-config`: File-based configuration scheme — one folder per tracked project containing metadata, predefined questions, and per-project notification overrides
- `change-tracker`: Python pipeline that fetches GitHub releases/changelogs and scrapes non-GitHub changelogs, then uses an LLM to summarize changes and answer configured questions
- `alternatives-discovery`: LLM + web search step that surfaces and briefly reviews alternative projects for each tracked project
- `diff-and-notify`: Compares current pipeline output to the previous run, detects important changes (answer flips, breaking-change keywords), and sends notifications via ntfy.sh with global + per-project config
- `web-ui`: Static HTML/JS dashboard served on GitHub Pages showing per-project summaries, Q&A answers, alternatives, and change history
- `github-actions-workflow`: CI/CD workflows for scheduled and manual pipeline runs (all projects or a specific project), with write-back of results to the repo

### Modified Capabilities

_(none — this is a greenfield project)_

## Impact

- **New repository structure**: `projects/<name>/` folders, `global-config.json`, and `data/<name>/` output directories committed by Actions
- **Python dependencies**: `requests`, `PyGitHub`, `beautifulsoup4`, `openai`, `anthropic`, `pydantic`
- **GitHub Actions secrets**: `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`), `NTFY_TOKEN`, `GITHUB_TOKEN` (built-in)
- **GitHub Pages**: enabled on the repo, serving from `docs/` or a `gh-pages` branch populated by Actions
- **External services**: ntfy.sh (push notifications), OpenAI or Anthropic API (LLM), optional search API for alternatives discovery
