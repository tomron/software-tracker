from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent


def save_project_output(
    slug: str,
    output: dict[str, Any],
    repo_root: Path | None = None,
) -> None:
    root = repo_root or REPO_ROOT
    data_dir = root / "data" / slug
    data_dir.mkdir(parents=True, exist_ok=True)

    latest_path = data_dir / "latest.json"
    previous_path = data_dir / "previous.json"

    if latest_path.exists():
        previous_path.write_text(latest_path.read_text())

    output["run_at"] = datetime.now(timezone.utc).isoformat()
    output["project_slug"] = slug
    _write_json(latest_path, output)

    docs_data_dir = root / "docs" / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)
    _write_json(docs_data_dir / f"{slug}.json", output)


def update_index(repo_root: Path | None = None) -> None:
    root = repo_root or REPO_ROOT
    projects_dir = root / "projects"
    index: list[dict[str, str]] = []
    if projects_dir.is_dir():
        for project_dir in sorted(projects_dir.iterdir()):
            config_file = project_dir / "config.json"
            if not config_file.exists():
                continue
            try:
                raw = json.loads(config_file.read_text())
                name = raw.get("name") or project_dir.name
                index.append({"slug": project_dir.name, "name": name})
            except (json.JSONDecodeError, KeyError):
                index.append({"slug": project_dir.name, "name": project_dir.name})

    docs_data_dir = root / "docs" / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)
    _write_json(docs_data_dir / "index.json", index)


def load_previous_output(slug: str, repo_root: Path | None = None) -> dict[str, Any] | None:
    root = repo_root or REPO_ROOT
    previous_path = root / "data" / slug / "previous.json"
    if not previous_path.exists():
        return None
    try:
        return json.loads(previous_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
