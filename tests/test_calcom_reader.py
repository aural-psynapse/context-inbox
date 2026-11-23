import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("calcom", os.path.join(REPO, "integrations", "calcom", "reader.py"))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

SRC = {"id": "cal", "channels": [{"id": "all", "feeds": ["crm"]}, {"id": "intro-call", "feeds": ["crm"]}]}


def booking(uid, created, updated=None, status="accepted", slug="intro-call", **extra):
    return {
        "uid": uid,
        "title": f"Call {uid}",
        "status": status,
        "start": "2026-12-01T10:00:00.000Z",
        "duration": 30,
        "createdAt": created,
        "updatedAt": updated,
        "attendees": [{"name": "Mary Byrne", "email": "mary@shop.ie"}],
        "eventType": {"id": 1, "slug": slug},
        **extra,
    }


class FakeApi:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, params):
        self.calls.append(dict(params))
        key = "updated" if "afterUpdatedAt" in params else "created"
        pages = self.pages.get(key, [[]])
        index = 1 if params.get("cursor") else 0
        has_more = index + 1 < len(pages)
        return {"status": "success", "data": pages[index],
                "pagination": {"hasMore": has_more, "nextCursor": "next" if has_more else None}}


class CalcomReaderTest(unittest.TestCase):
    def run_reader(self, api, cursors, started=2_000_000_000):
        with tempfile.TemporaryDirectory() as d:
            ok = reader.read(SRC, cursors, Path(d), api, started)
            out = {p.stem: [json.loads(x) for x in p.read_text().splitlines()] for p in Path(d).glob("*.jsonl")}
        return ok, out

    def test_first_run_reads_every_page_oldest_first(self):
        api = FakeApi({"created": [[booking("b2", "2026-11-02T09:00:00.000Z")],
                                   [booking("b1", "2026-11-01T09:00:00.000Z", slug="other")]]})
        cursors = {}

        ok, out = self.run_reader(api, cursors)

        self.assertTrue(ok)
        self.assertEqual([m["thread_ts"] for m in out["all"]], ["b1", "b2"])
        self.assertEqual([m["thread_ts"] for m in out["intro-call"]], ["b2"])
        first = out["all"][0]
        self.assertTrue(first["text"].startswith("New booking: Call b1. Starts 2026-12-01 10:00 UTC, 30 minutes."))
        self.assertIn("Booked by Mary Byrne <mary@shop.ie>.", first["text"])
        self.assertEqual(first["link"], "https://app.cal.com/booking/b1")
        self.assertEqual(first["feeds"], ["crm"])
        self.assertEqual(cursors["all"], "2026-11-02T09:00:00.000Z")

    def test_later_run_asks_for_new_and_changed_bookings(self):
        cancelled = booking("b1", "2026-11-01T09:00:00.000Z", "2026-11-03T09:00:00.000Z",
                            status="cancelled", cancellationReason="No budget.")
        api = FakeApi({"created": [[]], "updated": [[cancelled]]})

        _, out = self.run_reader(api, {"all": "2026-11-02T09:00:00.000Z"})

        self.assertEqual({tuple(sorted(c)) for c in api.calls[:2]},
                         {("afterCreatedAt", "limit"), ("afterUpdatedAt", "limit")})
        message = out["all"][0]
        self.assertTrue(message["text"].startswith("Booking cancelled:"))
        self.assertIn("Reason given: No budget.", message["text"])
        self.assertEqual(message["ts"], "b1@2026-11-03T09:00:00.000Z")

    def test_cursor_never_passes_the_run_start(self):
        api = FakeApi({"created": [[booking("b1", "2030-01-01T00:00:00.000Z")]]})
        cursors = {}

        self.run_reader(api, cursors, started=1_800_000_000)

        self.assertEqual(cursors["all"], reader.iso(1_800_000_000 - 1))

    def test_failed_channel_keeps_its_cursor(self):
        def broken(params):
            raise RuntimeError("401")

        cursors = {"all": "2026-11-01T00:00:00.000Z"}
        ok, out = self.run_reader(broken, cursors)

        self.assertFalse(ok)
        self.assertEqual(out, {})
        self.assertEqual(cursors["all"], "2026-11-01T00:00:00.000Z")


if __name__ == "__main__":
    unittest.main()
