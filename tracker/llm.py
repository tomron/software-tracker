from __future__ import annotations

import json
import logging
from typing import Any

from .models import GlobalConfig, LlmConfig, ProjectConfig

logger = logging.getLogger(__name__)

LLM_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "answers": {"type": "object", "additionalProperties": {"type": "string"}},
        "breaking_changes": {"type": "boolean"},
        "breaking_excerpts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "answers", "breaking_changes", "breaking_excerpts"],
}


def analyse(
    changelog_text: str,
    questions: list[str],
    instructions: str,
    llm_cfg: LlmConfig,
    project_cfg: ProjectConfig | None = None,
) -> dict[str, Any]:
    prompt = _build_prompt(changelog_text, questions, instructions, project_cfg)
    for attempt in range(2):
        raw = _call_llm(prompt, llm_cfg)
        try:
            result = json.loads(raw)
            _validate_shape(result)
            return result
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            if attempt == 0:
                logger.warning("LLM returned invalid JSON, retrying: %s", exc)
            else:
                logger.error("LLM returned invalid JSON after retry; storing raw text.")
                return {
                    "summary": raw,
                    "answers": {},
                    "breaking_changes": False,
                    "breaking_excerpts": [],
                }
    # unreachable, but satisfies type checker
    return {"summary": "", "answers": {}, "breaking_changes": False, "breaking_excerpts": []}


def _build_prompt(
    changelog_text: str,
    questions: list[str],
    instructions: str,
    project_cfg: ProjectConfig | None = None,
) -> str:
    # Build project context block (links for the LLM to reference in the summary)
    project_block = ""
    if project_cfg:
        lines = [f"Project: {project_cfg.name}"]
        if project_cfg.repo:
            lines.append(f"Repository: {project_cfg.repo}")
        if project_cfg.homepage:
            lines.append(f"Homepage: {project_cfg.homepage}")
        if project_cfg.changelog_url:
            lines.append(f"Changelog: {project_cfg.changelog_url}")
        project_block = "\n".join(lines) + "\n\n"

    questions_block = ""
    if questions:
        formatted = "\n".join(f"- {q}" for q in questions)
        questions_block = f"\n\nAnswer the following questions based on the changelog (answer each with a short string):\n{formatted}"

    instructions_block = f"\n\nAdditional instructions:\n{instructions}" if instructions else ""

    return (
        "You are a software analyst. Analyse the following changelog/release notes and return a JSON object.\n\n"
        f"{project_block}"
        "Required JSON fields:\n"
        '- "summary": 2-4 sentence plain-text summary of the most notable recent changes. '
        "Include specific version numbers, release dates, and direct links to release notes or relevant URLs where available.\n"
        '- "answers": object mapping each question to a short answer string\n'
        '- "breaking_changes": true if any breaking/deprecated/removed changes are present\n'
        '- "breaking_excerpts": list of short excerpt strings (max 3) describing breaking changes, or empty list\n'
        f"{instructions_block}"
        f"{questions_block}\n\n"
        "Changelog text:\n"
        "---\n"
        f"{changelog_text[:12000]}\n"
        "---\n\n"
        "Respond with only valid JSON, no markdown fences."
    )


def _call_llm(prompt: str, llm_cfg: LlmConfig) -> str:
    api_key = llm_cfg.resolve_api_key()
    if llm_cfg.provider == "openai":
        return _call_openai(prompt, llm_cfg.model, api_key)
    return _call_anthropic(prompt, llm_cfg.model, api_key)


def _call_openai(prompt: str, model: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def _call_anthropic(prompt: str, model: str, api_key: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text if message.content else ""


def _validate_shape(result: Any) -> None:
    if not isinstance(result, dict):
        raise TypeError("Expected dict")
    result.setdefault("summary", "")
    result.setdefault("answers", {})
    result.setdefault("breaking_changes", False)
    result.setdefault("breaking_excerpts", [])


def effective_llm_config(global_cfg: GlobalConfig, project_cfg: ProjectConfig) -> LlmConfig:
    return project_cfg.llm or global_cfg.llm
