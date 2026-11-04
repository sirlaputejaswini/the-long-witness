"""Loader for the CASAS Aruba trace (Zenodo record 17180309, CC BY 4.0).

The trace is the physical ground truth for consequence anchoring: what
the home's sensors actually saw. This module parses it once and offers
three queries: which activity label was active at a moment, whether the
resident was home / away / asleep, and which sensor events fall inside
a time window.

Zones (kitchen, living room, bedroom) are not taken from any floor plan.
They are derived from the recording itself: the motion sensors that fire
most inside episodes carrying a given activity label. That derivation is
documented wherever the zones are used.
"""

import bisect
from collections import Counter
from datetime import datetime, timezone

FMT = "%Y-%m-%d %H:%M:%S.%f"


def parse_ts(text):
    """Parse an Aruba/decision timestamp to epoch seconds (naive = UTC)."""
    if "." in text:
        dt = datetime.strptime(text, FMT)
    else:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc).timestamp()


def iso(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime(FMT)[:-3]


class Trace:
    def __init__(self, path):
        self.times = []          # epoch seconds, sorted
        self.lines = []          # canonical event line: "<ts> <sensor> <value>"
        self.sensors = []        # sensor id per event
        intervals = []           # (start, end, label) activity intervals
        open_labels = {}
        with open(path) as fh:
            for raw in fh:
                parts = raw.split()
                if len(parts) < 4:
                    continue
                ts_text = parts[0] + " " + parts[1]
                sensor, value = parts[2], parts[3]
                epoch = parse_ts(ts_text)
                self.times.append(epoch)
                self.sensors.append(sensor)
                self.lines.append(ts_text + " " + sensor + " " + value)
                if len(parts) >= 6 and parts[-1] in ("begin", "end"):
                    label = parts[-2]
                    if parts[-1] == "begin":
                        open_labels[label] = epoch
                    elif label in open_labels:
                        intervals.append((open_labels.pop(label), epoch, label))
        self.intervals = sorted(intervals)
        self._istarts = [iv[0] for iv in self.intervals]
        self._away_spans = self._build_away_spans()
        self._astarts = [s for s, _ in self._away_spans]
        self.zones = self._derive_zones()

    def _build_away_spans(self):
        # Resident is away from a Leave_Home begin until the next
        # Enter_Home begin.
        spans, away_from = [], None
        for start, _end, label in self.intervals:
            if label == "Leave_Home":
                away_from = start
            elif label == "Enter_Home" and away_from is not None:
                spans.append((away_from, start))
                away_from = None
        if away_from is not None:
            spans.append((away_from, self.times[-1]))
        return spans

    def _derive_zones(self):
        counts = {"Meal_Preparation": Counter(), "Relax": Counter(),
                  "Sleeping": Counter()}
        for start, end, label in self.intervals:
            if label not in counts:
                continue
            lo = bisect.bisect_left(self.times, start)
            hi = bisect.bisect_right(self.times, end)
            for i in range(lo, hi):
                s = self.sensors[i]
                if s.startswith("M"):
                    counts[label][s] += 1
        return {
            "kitchen": sorted(s for s, _ in counts["Meal_Preparation"].most_common(8)),
            "living": sorted(s for s, _ in counts["Relax"].most_common(8)),
            "bedroom": sorted(s for s, _ in counts["Sleeping"].most_common(8)),
        }

    def activity_at(self, epoch):
        i = bisect.bisect_right(self._istarts, epoch) - 1
        while i >= 0:
            start, end, label = self.intervals[i]
            if start <= epoch <= end:
                return label
            if end < epoch and start < epoch - 86400:
                break
            i -= 1
        return None

    def resident_state(self, epoch):
        if self.activity_at(epoch) == "Sleeping":
            return "asleep"
        i = bisect.bisect_right(self._astarts, epoch) - 1
        if i >= 0 and self._away_spans[i][0] <= epoch <= self._away_spans[i][1]:
            return "away"
        return "home"

    def window(self, t0, t1):
        """Indices of events with t0 <= t < t1."""
        lo = bisect.bisect_left(self.times, t0)
        hi = bisect.bisect_left(self.times, t1)
        return lo, hi
