import unittest

from counter import ENTRY, EXIT, Detection, LineCounter, get_current_statistics


def make_counter(**kw):
    ticks = iter(range(1000, 100000))
    kw.setdefault("clock", lambda: float(next(ticks)))
    return LineCounter(line_y=100, margin=5, **kw)


class LineCounterTests(unittest.TestCase):
    def test_entry_when_moving_down(self):
        c = make_counter()
        c.update(1, 50, 80)
        event = c.update(1, 50, 120)
        self.assertEqual(event.event_type, ENTRY)
        stats = c.get_statistics()
        self.assertEqual((stats["total_entries"], stats["total_exits"]), (1, 0))

    def test_exit_when_moving_up(self):
        c = make_counter()
        c.update(1, 50, 120)
        event = c.update(1, 50, 80)
        self.assertEqual(event.event_type, EXIT)
        stats = c.get_statistics()
        self.assertEqual((stats["total_entries"], stats["total_exits"]), (0, 1))

    def test_entry_direction_can_be_flipped(self):
        c = make_counter(entry_direction="up")
        c.update(1, 50, 120)
        self.assertEqual(c.update(1, 50, 80).event_type, ENTRY)

    def test_same_crossing_counted_once(self):
        c = make_counter()
        for y in (80, 90, 120, 130, 140, 150):
            c.update(1, 50, y)
        self.assertEqual(c.get_statistics()["total_entries"], 1)

    def test_jitter_inside_deadband_is_ignored(self):
        c = make_counter()
        c.update(1, 50, 80)
        for y in (97, 103, 98, 102, 99, 101):  # wobbling on the line
            self.assertIsNone(c.update(1, 50, y))
        self.assertEqual(c.get_statistics()["total_entries"], 0)
        c.update(1, 50, 120)  # finally clearly across
        self.assertEqual(c.get_statistics()["total_entries"], 1)

    def test_jitter_near_line_after_crossing_not_recounted(self):
        c = make_counter()
        c.update(1, 50, 80)
        c.update(1, 50, 120)
        for y in (106, 103, 108, 104, 110):
            c.update(1, 50, y)
        stats = c.get_statistics()
        self.assertEqual((stats["total_entries"], stats["total_exits"]), (1, 0))

    def test_touching_line_without_crossing_is_not_counted(self):
        c = make_counter()
        c.update(1, 50, 80)
        c.update(1, 50, 100)
        c.update(1, 50, 80)
        self.assertEqual(c.get_statistics()["total_entries"], 0)
        self.assertEqual(c.get_statistics()["total_exits"], 0)

    def test_real_back_and_forth_is_two_events(self):
        c = make_counter()
        c.update(1, 50, 80)
        c.update(1, 50, 120)
        c.update(1, 50, 80)
        stats = c.get_statistics()
        self.assertEqual((stats["total_entries"], stats["total_exits"]), (1, 1))

    def test_object_first_seen_past_line_is_not_counted(self):
        c = make_counter()
        c.update(1, 50, 150)
        c.update(1, 50, 160)
        self.assertEqual(c.get_statistics()["total_entries"], 0)

    def test_multiple_objects_in_one_frame(self):
        c = make_counter()
        c.process_frame([Detection(1, 10, 80), Detection(2, 20, 120)])
        events = c.process_frame([Detection(1, 10, 120), Detection(2, 20, 80)])
        self.assertEqual(sorted(e.event_type for e in events), [ENTRY, EXIT])

    def test_object_wise_counts(self):
        c = make_counter()
        c.update("a", 0, 80, "person")
        c.update("a", 0, 120, "person")  # ENTRY
        c.update("a", 0, 80, "person")  # EXIT
        c.update("b", 0, 80, "car")
        c.update("b", 0, 120, "car")  # ENTRY
        stats = c.get_statistics()
        self.assertEqual(
            stats["object_counts"]["a"], {"label": "person", "entries": 1, "exits": 1}
        )
        self.assertEqual(
            stats["object_counts"]["b"], {"label": "car", "entries": 1, "exits": 0}
        )
        self.assertEqual(stats["label_counts"]["person"], {"entries": 1, "exits": 1})
        self.assertEqual(stats["label_counts"]["car"], {"entries": 1, "exits": 0})

    def test_recent_events_newest_first_and_capped(self):
        c = make_counter(max_recent_events=3)
        for oid in range(5):
            c.update(oid, 0, 80)
            c.update(oid, 0, 120)
        recent = c.get_statistics()["recent_events"]
        self.assertEqual(len(recent), 3)
        self.assertEqual([e["object_id"] for e in recent], [4, 3, 2])
        self.assertEqual(c.get_statistics()["total_entries"], 5)

    def test_current_objects_expire_when_missing(self):
        c = make_counter(max_missing_frames=2)
        c.process_frame([Detection(1, 0, 80), Detection(2, 0, 80)])
        for _ in range(3):
            c.process_frame([Detection(2, 0, 80)])
        ids = [o["object_id"] for o in c.get_statistics()["current_objects"]]
        self.assertEqual(ids, [2])

    def test_line_x_range_limits_counting(self):
        c = make_counter(line_x_range=(0, 100))
        c.update(1, 500, 80)
        c.update(1, 500, 120)  # crosses outside the line segment
        self.assertEqual(c.get_statistics()["total_entries"], 0)
        c.update(2, 50, 80)
        c.update(2, 50, 120)
        self.assertEqual(c.get_statistics()["total_entries"], 1)

    def test_statistics_shape_and_helper(self):
        c = make_counter()
        c.update(1, 0, 80)
        c.update(1, 0, 120)
        stats = get_current_statistics(c)
        self.assertEqual(
            set(stats),
            {
                "current_objects",
                "current_count",
                "total_entries",
                "total_exits",
                "net_count",
                "object_counts",
                "label_counts",
                "recent_events",
            },
        )
        self.assertEqual(stats["current_count"], 1)
        self.assertEqual(stats["net_count"], 1)

    def test_reset(self):
        c = make_counter()
        c.update(1, 0, 80)
        c.update(1, 0, 120)
        c.reset()
        stats = c.get_statistics()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["current_objects"], [])
        self.assertEqual(stats["recent_events"], [])

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            LineCounter(line_y=10, entry_direction="left")
        with self.assertRaises(ValueError):
            LineCounter(line_y=10, margin=-1)


if __name__ == "__main__":
    unittest.main()
