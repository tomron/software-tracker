from __future__ import annotations

import argparse
import logging
import sys

from .alternatives import discover_alternatives
from .config import (
    discover_projects,
    effective_notify,
    load_global_config,
    merge_instructions,
    merge_questions,
)
from .diff import compute_events, error_event
from .fetcher import RateLimitError, fetch_changelog
from .llm import analyse, effective_llm_config
from .notify import send_notifications
from .storage import load_previous_output, save_project_output, update_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Software project tracker")
    parser.add_argument(
        "--project",
        metavar="SLUG",
        help="Run only for this project slug (default: all projects)",
    )
    args = parser.parse_args()

    global_cfg = load_global_config()

    # Validate LLM API key before doing any work
    try:
        global_cfg.llm.resolve_api_key()
    except EnvironmentError as exc:
        logger.error("Missing API key: %s", exc)
        sys.exit(1)

    all_projects = discover_projects()
    if not all_projects:
        logger.warning("No projects found under projects/. Add a folder with config.json.")
        sys.exit(0)

    if args.project:
        slugs = {slug for slug, _ in all_projects}
        if args.project not in slugs:
            logger.error(
                "Unknown project slug '%s'. Available: %s",
                args.project,
                ", ".join(sorted(slugs)),
            )
            sys.exit(1)
        projects = [(s, c) for s, c in all_projects if s == args.project]
    else:
        projects = all_projects

    counts = {"success": 0, "skipped": 0, "error": 0}

    for slug, project_cfg in projects:
        logger.info("Processing project: %s", slug)
        notify_cfg = effective_notify(global_cfg, project_cfg)
        global_notify_cfg = global_cfg.notify if project_cfg.notify is not None else None
        llm_cfg = effective_llm_config(global_cfg, project_cfg)
        questions = merge_questions(global_cfg, project_cfg)
        instructions = merge_instructions(global_cfg, project_cfg)

        try:
            # Fetch
            try:
                changelog_text = fetch_changelog(project_cfg)
            except RateLimitError as exc:
                logger.error("[%s] %s", slug, exc)
                events = [error_event(project_cfg.name, "fetch", str(exc))]
                send_notifications(events, notify_cfg, global_notify_cfg)
                counts["skipped"] += 1
                continue

            # Analyse
            llm_result = analyse(changelog_text, questions, instructions, llm_cfg)

            # Alternatives
            alternatives = discover_alternatives(project_cfg, llm_cfg, global_cfg.search)

            # Build output
            output = {
                "name": project_cfg.name,
                "summary": llm_result["summary"],
                "answers": llm_result["answers"],
                "breaking_changes": llm_result["breaking_changes"],
                "breaking_excerpts": llm_result["breaking_excerpts"],
                "alternatives": alternatives,
            }

            # Save and diff
            previous = load_previous_output(slug)
            save_project_output(slug, output)
            events = compute_events(project_cfg.name, output, previous)
            send_notifications(events, notify_cfg, global_notify_cfg)
            counts["success"] += 1
            logger.info("[%s] Done.", slug)

        except Exception as exc:
            logger.exception("[%s] Unexpected error", slug)
            events = [error_event(project_cfg.name, "pipeline", str(exc))]
            send_notifications(events, notify_cfg, global_notify_cfg)
            counts["error"] += 1

    update_index()
    logger.info(
        "Run complete. success=%d skipped=%d error=%d",
        counts["success"],
        counts["skipped"],
        counts["error"],
    )
    if counts["error"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
