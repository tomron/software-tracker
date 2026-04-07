from __future__ import annotations

import json
import logging
from typing import Any

from .models import AlternativeEntry, GlobalConfig, LlmConfig, ProjectConfig, SearchConfig

logger = logging.getLogger(__name__)


def discover_alternatives(
    project_cfg: ProjectConfig,
    llm_cfg: LlmConfig,
    search_cfg: SearchConfig,
) -> list[dict]:
    search_api_key = search_cfg.resolve_api_key()
    config_entries = _config_alternatives(project_cfg)
    discovered = _discover_via_llm(project_cfg, llm_cfg, search_api_key)
    return _merge(config_entries, discovered)


def _config_alternatives(project_cfg: ProjectConfig) -> list[dict]:
    results = []
    for alt in project_cfg.alternatives:
        results.append({
            "name": alt.name,
            "url": alt.links[0] if alt.links else "",
            "review": alt.comment,
            "source": "config",
            "features": {},
        })
    return results


def _discover_via_llm(
    project_cfg: ProjectConfig,
    llm_cfg: LlmConfig,
    search_api_key: str | None,
) -> list[dict]:
    source = "web_search" if search_api_key else "llm_only"
    prompt = _build_alternatives_prompt(project_cfg, search_api_key is not None)
    try:
        api_key = llm_cfg.resolve_api_key()
        if llm_cfg.provider == "openai":
            raw = _call_openai_with_search(prompt, llm_cfg.model, api_key, search_api_key)
        else:
            raw = _call_anthropic_with_search(prompt, llm_cfg.model, api_key, search_api_key)
        entries = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(entries, list):
            return []
        return [
            {
                "name": e.get("name", ""),
                "url": e.get("url", ""),
                "review": e.get("review", ""),
                "source": source,
                "features": e.get("features") if isinstance(e.get("features"), dict) else {},
            }
            for e in entries
            if e.get("name")
        ]
    except Exception as exc:
        logger.warning("Alternatives discovery failed: %s", exc)
        return []


def _build_alternatives_prompt(project_cfg: ProjectConfig, use_search: bool) -> str:
    search_note = (
        "You have access to a web search tool. Perform up to 3 searches to find current alternatives."
        if use_search
        else "Based on your training data, suggest alternatives."
    )
    return (
        f"You are a software analyst. {search_note}\n\n"
        f"Project: {project_cfg.name}\n"
        f"Description: {project_cfg.description or 'No description provided.'}\n\n"
        "Return a JSON array of alternative projects. Each entry must be a JSON object with:\n"
        '- "name": project name (string, required)\n'
        '- "url": homepage or repo URL (string, optional)\n'
        '- "review": one sentence describing trade-offs vs the main project (string, required)\n'
        '- "features": object mapping 4-6 key feature names to true/false booleans indicating '
        "whether the alternative supports that feature. Choose features that are most relevant "
        "for comparing alternatives to the main project (e.g. self-hosted, open-source, "
        "cloud-hosted, SSO, free tier, etc.). Use consistent feature names across all entries.\n\n"
        "Return at most 5 alternatives. Respond with only a valid JSON array, no markdown fences."
    )


def _call_openai_with_search(
    prompt: str, model: str, api_key: str, search_api_key: str | None
) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    tools: list[dict[str, Any]] = []
    if search_api_key:
        tools = [{"type": "web_search_preview"}]

    if tools:
        response = client.chat.completions.create(
            model=model,
            tools=tools,  # type: ignore[arg-type]
            messages=[{"role": "user", "content": prompt}],
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    content = response.choices[0].message.content or "[]"
    # The response may be wrapped in {"alternatives": [...]} — unwrap if needed
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return content
        for v in parsed.values():
            if isinstance(v, list):
                return json.dumps(v)
    except json.JSONDecodeError:
        pass
    return content


def _call_anthropic_with_search(
    prompt: str, model: str, api_key: str, search_api_key: str | None
) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    tools: list[dict[str, Any]] = []
    if search_api_key:
        tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        kwargs["tools"] = tools

    message = client.messages.create(**kwargs)
    for block in message.content:
        if hasattr(block, "text"):
            return block.text
    return "[]"


def _merge(
    config_entries: list[dict],
    discovered: list[dict],
) -> list[dict]:
    config_names_lower = {e["name"].lower() for e in config_entries}
    deduped_discovered = [
        e for e in discovered if e["name"].lower() not in config_names_lower
    ]
    return config_entries + deduped_discovered
