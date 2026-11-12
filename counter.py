"""Virtual horizontal counting line.

Feed it object positions frame by frame (e.g. from any tracker that gives each
object a stable ID). When an object moves from one side of the line to the
other, an ENTRY or EXIT is recorded -- exactly once per crossing.

Coordinates follow image convention: y grows downward.
By default, moving DOWN across the line is an ENTRY and moving UP is an EXIT
(change with ``entry_direction="up"``).

How double counting is avoided
------------------------------
* A dead-band of ``margin`` pixels surrounds the line. An object's "side" only
  changes once it is clearly beyond the band, so jitter around the line, or
  an object hovering on it, never produces repeated counts.
* The side is remembered per object ID, so a crossing is counted only when the
  confirmed side flips. An object that appears already past the line is not
  counted.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from counting_statistics import (  # local statistics.py
    ENTRY,
    EXIT,
    CountingStatistics,
    CrossingEvent,
    build_statistics_snapshot,
)

__all__ = ["Detection", "LineCounter", "get_current_statistics", "ENTRY", "EXIT"]


@dataclass(frozen=True)
class Detection:
    """One tracked object observed in a frame."""

    object_id: Any
    x: float
    y: float
    label: str = "object"


@dataclass
class _Track:
    object_id: Any
    label: str
    x: float
    y: float
    side: int  # -1 above the line, +1 below, 0 = not yet known
    last_seen_frame: int


class LineCounter:
    def __init__(
        self,
        line_y: float,
        margin: float = 5.0,
        entry_direction: str = "down",
        line_x_range: Optional[Tuple[float, float]] = None,
        max_missing_frames: int = 30,
        max_recent_events: int = 50,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if entry_direction not in ("down", "up"):
            raise ValueError("entry_direction must be 'down' or 'up'")
        if margin < 0:
            raise ValueError("margin must be >= 0")
        if line_x_range is not None and line_x_range[0] > line_x_range[1]:
            raise ValueError("line_x_range must be (min_x, max_x)")

        self.line_y = line_y
        self.margin = margin
        self.entry_direction = entry_direction
        self.line_x_range = line_x_range
        self.max_missing_frames = max_missing_frames
        self._clock = clock

        self._stats = CountingStatistics(max_recent_events=max_recent_events)
        self._tracks: Dict[Any, _Track] = {}
        self._frame = 0
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ input
    def process_frame(self, detections: Iterable[Detection]) -> List[CrossingEvent]:
        """Process all objects seen in one frame. Returns events from this frame."""
        events: List[CrossingEvent] = []
        with self._lock:
            self._frame += 1
            for det in detections:
                event = self._update_track(det)
                if event is not None:
                    events.append(event)
            self._expire_tracks()
        return events

    def update(
        self, object_id: Any, x: float, y: float, label: str = "object"
    ) -> Optional[CrossingEvent]:
        """Convenience for a single object (counts as its own frame)."""
        events = self.process_frame([Detection(object_id, x, y, label)])
        return events[0] if events else None

    # --------------------------------------------------------------- internals
    def _side_of(self, y: float) -> int:
        if y > self.line_y + self.margin:
            return 1
        if y < self.line_y - self.margin:
            return -1
        return 0  # inside the dead-band

    def _in_line_span(self, x: float) -> bool:
        if self.line_x_range is None:
            return True
        return self.line_x_range[0] <= x <= self.line_x_range[1]

    def _update_track(self, det: Detection) -> Optional[CrossingEvent]:
        side = self._side_of(det.y)
        track = self._tracks.get(det.object_id)

        if track is None:
            self._tracks[det.object_id] = _Track(
                det.object_id, det.label, det.x, det.y, side, self._frame
            )
            return None

        previous_side = track.side
        track.x, track.y = det.x, det.y
        track.label = det.label
        track.last_seen_frame = self._frame

        if side == 0:
            return None  # still in the dead-band: keep the last confirmed side

        track.side = side
        if previous_side == 0 or previous_side == side:
            return None
        if not self._in_line_span(det.x):
            return None  # went around the end of the line segment

        moved_down = previous_side == -1 and side == 1
        is_entry = moved_down if self.entry_direction == "down" else not moved_down
        event = CrossingEvent(
            event_type=ENTRY if is_entry else EXIT,
            object_id=det.object_id,
            label=det.label,
            timestamp=self._clock(),
            position=(det.x, det.y),
        )
        self._stats.record(event)
        return event

    def _expire_tracks(self) -> None:
        cutoff = self._frame - self.max_missing_frames
        stale = [oid for oid, t in self._tracks.items() if t.last_seen_frame < cutoff]
        for oid in stale:
            del self._tracks[oid]

    # ----------------------------------------------------------------- output
    def current_objects(self) -> List[Dict[str, Any]]:
        """Objects currently tracked (seen within ``max_missing_frames``)."""
        with self._lock:
            return [
                {
                    "object_id": t.object_id,
                    "label": t.label,
                    "x": t.x,
                    "y": t.y,
                    "side": {-1: "above", 1: "below", 0: "unknown"}[t.side],
                }
                for t in self._tracks.values()
            ]

    def get_statistics(self) -> Dict[str, Any]:
        """Snapshot for the dashboard.

        Keys: current_objects, current_count, total_entries, total_exits,
        net_count, object_counts, label_counts, recent_events (newest first).
        """
        with self._lock:
            return build_statistics_snapshot(self._stats, self.current_objects())

    def reset(self) -> None:
        with self._lock:
            self._stats.reset()
            self._tracks.clear()
            self._frame = 0


def get_current_statistics(counter: LineCounter) -> Dict[str, Any]:
    """Module-level helper: current statistics for ``counter``."""
    return counter.get_statistics()
