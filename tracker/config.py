from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .models import GlobalConfig, NotifyConfig, ProjectConfig

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent


def load_global_config(path: Path | None = None) -> GlobalConfig:
    config_path = path or REPO_ROOT / "global-config.json"
    if not config_path.exists():
        logger.info("No global-config.json found; using built-in defaults.")
        return GlobalConfig()
    try:
        raw = json.loads(config_path.read_text())
        # Strip _comment keys (used for inline documentation)
        raw = _strip_comments(raw)
        return GlobalConfig.model_validate(raw)
    except json.JSONDecodeError as exc:
        logger.error("global-config.json is invalid JSON: %s", exc)
        return GlobalConfig()
    except ValidationError as exc:
        logger.error("global-config.json failed validation: %s", exc)
        return GlobalConfig()


def discover_projects(projects_dir: Path | None = None) -> list[tuple[str, ProjectConfig]]:
    base = projects_dir or REPO_ROOT / "projects"
    results: list[tuple[str, ProjectConfig]] = []
    if not base.is_dir():
        logger.warning("Projects directory not found: %s", base)
        return results
    for project_dir in sorted(base.iterdir()):
        if not project_dir.is_dir():
            continue
        config_file = project_dir / "config.json"
        if not config_file.exists():
            logger.warning("No config.json in %s — skipping.", project_dir.name)
            continue
        try:
            raw = json.loads(config_file.read_text())
            raw = _strip_comments(raw)
            config = ProjectConfig.model_validate(raw)
            results.append((project_dir.name, config))
        except json.JSONDecodeError as exc:
            logger.error("[%s] config.json is invalid JSON: %s", project_dir.name, exc)
        except ValidationError as exc:
            logger.error("[%s] config.json failed validation:\n%s", project_dir.name, exc)
    return results


def merge_questions(global_cfg: GlobalConfig, project_cfg: ProjectConfig) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for q in global_cfg.questions + project_cfg.questions:
        if q not in seen:
            seen.add(q)
            merged.append(q)
    return merged


def effective_notify(global_cfg: GlobalConfig, project_cfg: ProjectConfig) -> NotifyConfig:
    return project_cfg.notify if project_cfg.notify is not None else global_cfg.notify


def merge_instructions(global_cfg: GlobalConfig, project_cfg: ProjectConfig) -> str:
    parts = [p for p in [global_cfg.instructions, project_cfg.instructions] if p]
    return "\n\n".join(parts)


def resolve_llm_api_key(global_cfg: GlobalConfig, project_cfg: ProjectConfig) -> str:
    llm = project_cfg.llm or global_cfg.llm
    return llm.resolve_api_key()


def _strip_comments(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_comments(i) for i in obj]
    return obj
