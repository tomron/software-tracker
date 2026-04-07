from __future__ import annotations

import logging
import os

import requests

from .diff import DiffEvent
from .models import NotifyConfig

logger = logging.getLogger(__name__)

NTFY_BASE = "https://ntfy.sh"


def send_notifications(
    events: list[DiffEvent],
    notify_cfg: NotifyConfig,
    global_notify_cfg: NotifyConfig | None = None,
) -> None:
    for event in events:
        cfg = notify_cfg if event.type in notify_cfg.on else None
        if cfg is None and global_notify_cfg and event.type in global_notify_cfg.on:
            cfg = global_notify_cfg
        if cfg is None or not cfg.topics:
            continue
        title, body = _format_notification(event)
        for topic in cfg.topics:
            _post(topic, title, body)


def _format_notification(event: DiffEvent) -> tuple[str, str]:
    name = event.project_name
    if event.type == "answer_changed":
        q = event.data.get("question", "")
        old = event.data.get("old", "")
        new = event.data.get("new", "")
        return (
            f"[{name}] Answer changed",
            f"Question: {q}\nBefore: {old}\nAfter:  {new}",
        )
    if event.type == "breaking_change":
        excerpts = event.data.get("excerpts", [])
        body = "Breaking changes detected."
        if excerpts:
            body += "\n\n" + "\n• ".join([""] + excerpts[:3]).lstrip()
        return f"[{name}] Breaking change detected", body
    if event.type == "run_complete":
        run_at = event.data.get("run_at", "")
        summary = event.data.get("summary", "")
        first_sentence = summary.split(".")[0] + "." if summary else "No summary."
        return (
            f"[{name}] Run complete",
            f"Run at: {run_at}\n{first_sentence}",
        )
    if event.type == "error":
        step = event.data.get("step", "unknown")
        message = event.data.get("message", "")
        return (
            f"[{name}] Pipeline error",
            f"Step: {step}\nError: {message}",
        )
    return f"[{name}] {event.type}", str(event.data)


def _post(topic: str, title: str, body: str) -> None:
    headers: dict[str, str] = {
        "Title": title,
        "Content-Type": "text/plain",
    }
    token = os.environ.get("NTFY_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.post(
            f"{NTFY_BASE}/{topic}",
            data=body.encode(),
            headers=headers,
            timeout=10,
        )
        if not resp.ok:
            logger.warning("ntfy.sh POST to topic '%s' failed: HTTP %s", topic, resp.status_code)
    except requests.RequestException as exc:
        logger.warning("ntfy.sh POST to topic '%s' failed: %s", topic, exc)
