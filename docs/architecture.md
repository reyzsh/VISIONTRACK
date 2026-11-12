# System Architecture — Object Entry/Exit Counter

## Overview

The system observes a camera/video stream, detects supported objects, associates detections over time, determines when an object's movement crosses a configured counting line, and records confirmed ENTRY/EXIT events. The event logger in this deliverable is deliberately downstream of detection and tracking; it does not inspect frames, infer crossings, or alter tracking behavior.

## Logical components

1. **Video source** — Live camera or prerecorded video. Supplies timestamped frames and reports source availability.
2. **Frame acquisition** — Reads frames and forwards them to the existing vision pipeline; surfaces camera/read errors.
3. **Object detection** — Existing, unchanged component that emits class-labelled detections and positions for each frame.
4. **Object tracking** — Existing, unchanged component that associates detections across frames and maintains track identity/state.
5. **Crossing/event decision** — Existing system logic evaluates track movement relative to the configured line and direction. It should emit a confirmed event only once for each crossing according to the system's duplicate-suppression policy.
6. **Event logger (`event_logger.py`)** — Receives confirmed event calls and appends rows to a CSV with columns `ID,Object,Event,Time`. Uses local wall-clock time by default; caller may supply a `datetime` for deterministic tests. Creates the parent directory as needed and appends to an existing file.
7. **Event CSV / reporting** — Persistent event rows are available to downstream reports, audits, and count reconciliation.
8. **Health/diagnostics** — Reports camera availability and processing/logging errors through the application's existing mechanism.

## Data flow

- Frames flow from source through acquisition, detection, and tracking.
- Track states flow to the existing line-crossing decision logic.
- Only confirmed events flow to the logger; the logger never calls detection or tracking.
- The logger serializes each event as one CSV row. It creates the header for a new/empty file and assigns an ID based on the highest readable existing ID.
- CSV records persist on local storage at the configured path. Protect the path with suitable access controls and backups if used operationally.

## Event CSV contract

Header: `ID,Object,Event,Time`

Example rows:

    1,person,ENTRY,15:30:21
    2,person,EXIT,15:31:04

IDs are positive integers and increase for each appended event. `Object` is the class/name supplied by the caller. `Event` is trimmed and uppercased by the logger. `Time` is local `HH:MM:SS`; it does not include a date or timezone, so long-term/multi-day audit use should include an externally recorded date or extend the agreed schema in a future change.

## Integration boundary

The detection, tracking, and crossing logic are not changed. Integrate by constructing `EventLogger` once with the desired CSV path and calling `log_event(object_name, event)` only when upstream logic confirms ENTRY or EXIT. The logger raises `ValueError` for blank object/event values and allows I/O errors to propagate so the host application can report them. Its lock protects concurrent calls within one process; multiple independent processes writing the same CSV are not coordinated.

## Reliability and operational considerations

- On camera failure, the source/host system should signal unavailable input and avoid generating events from absent frames. Recovery behavior belongs to the host application and should be tested without replay-induced duplicate events.
- A CSV write failure must be surfaced by the calling application; do not silently treat an event as persisted.
- The logger's ID scan is suitable for modest event logs. For very large logs or multi-process writers, use a transactional database or coordinated ID service rather than changing detection/tracking logic.
- Because the schema stores time-of-day only, event chronology across midnight cannot be determined from CSV alone.

## Trust boundaries

Frames and class labels originate from external input and vision components. The logger validates required strings but does not verify event semantics, class membership, timestamps, or crossing correctness. Correct event generation and duplicate suppression remain responsibilities of upstream system logic.
