## ADDED Requirements

### Requirement: Diff current output against previous run
After each project's pipeline run, the system SHALL compare `data/<slug>/latest.json` against `data/<slug>/previous.json` to detect meaningful changes.

#### Scenario: Answer value changed
- **WHEN** the answer to a question differs between `previous.json` and `latest.json`
- **THEN** the diff records an `answer_changed` event with the question text, old value, and new value

#### Scenario: Breaking change newly detected
- **WHEN** `latest.json` has `breaking_changes: true` and `previous.json` has `breaking_changes: false` (or no previous run)
- **THEN** the diff records a `breaking_change` event with the `breaking_excerpts`

#### Scenario: No previous run
- **WHEN** `previous.json` does not exist for a project
- **THEN** no diff events are generated; notifications are not sent for the first run (except `run_complete` if configured)

#### Scenario: No changes detected
- **WHEN** `latest.json` and `previous.json` are semantically identical on tracked fields
- **THEN** no change-based diff events are recorded; a `run_complete` notification is still sent if configured

---

### Requirement: Notification rules evaluation
The system SHALL evaluate notification rules from the effective notify config (per-project override or global) to decide whether to send a notification for each event. The full set of supported event types in the `on` list is:

- `answer_changed` — an answer to a tracked question changed between runs
- `breaking_change` — breaking changes newly detected in release notes
- `run_complete` — the pipeline completed successfully for the project (fires every run)
- `error` — the pipeline encountered an error while processing the project

#### Scenario: Event matches a configured trigger
- **WHEN** a diff produces an `answer_changed` event and the effective notify config includes `"answer_changed"` in `on`
- **THEN** a notification is sent to all configured `topics`

#### Scenario: run_complete fires every run
- **WHEN** the pipeline successfully completes processing a project and `"run_complete"` is in the `on` list
- **THEN** a notification is sent regardless of whether any changes were detected, including a brief summary

#### Scenario: Event not in trigger list
- **WHEN** a diff produces a `breaking_change` event but the effective notify config's `on` list does not include `"breaking_change"`
- **THEN** no notification is sent for that event

#### Scenario: No notify config defined globally or per project
- **WHEN** neither `global-config.json` nor the project `config.json` defines a `notify` block
- **THEN** no notifications are sent regardless of events

---

### Requirement: Send notifications via ntfy.sh
The system SHALL send notifications by POSTing to `https://ntfy.sh/<topic>` with a plain-text message body and a title header.

#### Scenario: Notification sent for answer change
- **WHEN** an `answer_changed` event is triggered
- **THEN** the system POSTs to ntfy.sh with title `"[<project name>] Answer changed"` and body listing the question, old answer, and new answer

#### Scenario: Notification sent for breaking change
- **WHEN** a `breaking_change` event is triggered
- **THEN** the system POSTs to ntfy.sh with title `"[<project name>] Breaking change detected"` and body containing the breaking excerpts

#### Scenario: Notification sent on every successful run
- **WHEN** a `run_complete` event is triggered
- **THEN** the system POSTs to ntfy.sh with title `"[<project name>] Run complete"` and body containing the run timestamp and a one-line summary

#### Scenario: Notification sent on pipeline error
- **WHEN** the pipeline encounters an error while processing a project (fetch failure, LLM error, validation failure) and `"error"` is in the `on` list
- **THEN** the system POSTs to ntfy.sh with title `"[<project name>] Pipeline error"` and body containing the error message and step where it occurred

#### Scenario: Error notification uses global topic as fallback
- **WHEN** a project-level error occurs and the project has no `notify` block but the global config has `"error"` in `on`
- **THEN** the error notification is sent to the global topics

#### Scenario: ntfy.sh POST fails
- **WHEN** the ntfy.sh endpoint returns a non-2xx response
- **THEN** the system logs the failure and continues without retrying; the pipeline run is not marked as failed

#### Scenario: NTFY_TOKEN provided
- **WHEN** the `NTFY_TOKEN` environment variable is set
- **THEN** the system includes an `Authorization: Bearer <token>` header on all ntfy.sh requests
