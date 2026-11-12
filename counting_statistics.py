"""Statistics bookkeeping for the virtual line counter.

NOTE: this file is named ``statistics.py`` as requested. That is also the name
of a Python standard-library module, so keep this folder's files together and
don't put it on ``sys.path`` ahead of code that needs the stdlib version.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

ENTRY = "ENTRY"
EXIT = "EXIT"


@dataclass(frozen=True)
class CrossingEvent:
    """One recorded crossing of the counting line."""

    event_type: str  # ENTRY or EXIT
    object_id: Any
    label: str
    timestamp: float  # seconds since epoch
    position: Tuple[float, float]  # (x, y) where the crossing was confirmed

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["time"] = datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")
        return data


class CountingStatistics:
    """Aggregates crossing events into totals, per-object counts and a recent log."""

    def __init__(self, max_recent_events: int = 50) -> None:
        self._recent: Deque[CrossingEvent] = deque(maxlen=max_recent_events)
        self.reset()

    def reset(self) -> None:
        self.total_entries = 0
        self.total_exits = 0
        self._by_object: Dict[Any, Dict[str, Any]] = {}
        self._by_label: Dict[str, Dict[str, int]] = {}
        self._recent.clear()

    def record(self, event: CrossingEvent) -> None:
        key = "entries" if event.event_type == ENTRY else "exits"
        if event.event_type == ENTRY:
            self.total_entries += 1
        else:
            self.total_exits += 1

        obj = self._by_object.setdefault(
            event.object_id, {"label": event.label, "entries": 0, "exits": 0}
        )
        obj[key] += 1

        lab = self._by_label.setdefault(event.label, {"entries": 0, "exits": 0})
        lab[key] += 1

        self._recent.append(event)

    def object_counts(self) -> Dict[Any, Dict[str, Any]]:
        """Per-object counts: ``{object_id: {label, entries, exits}}``."""
        return {oid: dict(c) for oid, c in self._by_object.items()}

    def label_counts(self) -> Dict[str, Dict[str, int]]:
        """Per-class counts: ``{label: {entries, exits}}``."""
        return {lab: dict(c) for lab, c in self._by_label.items()}

    def recent_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Most recent events first, as plain dicts."""
        events = [e.to_dict() for e in reversed(self._recent)]
        return events if limit is None else events[:limit]


def build_statistics_snapshot(
    stats: CountingStatistics, current_objects: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Combine counters and the live object list into one dashboard-ready dict."""
    return {
        "current_objects": current_objects,
        "current_count": len(current_objects),
        "total_entries": stats.total_entries,
        "total_exits": stats.total_exits,
        "net_count": stats.total_entries - stats.total_exits,
        "object_counts": stats.object_counts(),
        "label_counts": stats.label_counts(),
        "recent_events": stats.recent_events(),
    }
