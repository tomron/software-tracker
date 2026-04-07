from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


EventType = Literal["answer_changed", "breaking_change", "run_complete", "error"]


@dataclass
class DiffEvent:
    type: EventType
    project_name: str
    data: dict[str, Any] = field(default_factory=dict)


def compute_events(
    project_name: str,
    latest: dict[str, Any],
    previous: dict[str, Any] | None,
) -> list[DiffEvent]:
    events: list[DiffEvent] = []

    if previous is not None:
        prev_answers: dict[str, str] = previous.get("answers") or {}
        curr_answers: dict[str, str] = latest.get("answers") or {}
        for question, curr_val in curr_answers.items():
            prev_val = prev_answers.get(question)
            if prev_val is not None and prev_val != curr_val:
                events.append(DiffEvent(
                    type="answer_changed",
                    project_name=project_name,
                    data={"question": question, "old": prev_val, "new": curr_val},
                ))

        prev_breaking = previous.get("breaking_changes", False)
        curr_breaking = latest.get("breaking_changes", False)
        if curr_breaking and not prev_breaking:
            events.append(DiffEvent(
                type="breaking_change",
                project_name=project_name,
                data={"excerpts": latest.get("breaking_excerpts", [])},
            ))

    events.append(DiffEvent(
        type="run_complete",
        project_name=project_name,
        data={
            "run_at": latest.get("run_at", ""),
            "summary": latest.get("summary", ""),
        },
    ))

    return events


def error_event(project_name: str, step: str, message: str) -> DiffEvent:
    return DiffEvent(
        type="error",
        project_name=project_name,
        data={"step": step, "message": message},
    )
