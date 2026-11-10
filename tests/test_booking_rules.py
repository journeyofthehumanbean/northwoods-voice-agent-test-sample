"""Policy checks for the Example Plumbing Co sample fixtures."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.booking_tool import BookingTool
from harness.engine import RULE_CONFIRM, RULE_DECLINE, RULE_SMS, PolicyHarness

FLOW = ROOT / "flows" / "example_plumbing_co.json"
RAW = json.loads((ROOT / "fixtures" / "calls.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "examples" / "make_webhook_payload.json").read_text(encoding="utf-8"))


def load_fixture(name: str) -> dict:
    case = RAW["cases"][name]
    events = list(RAW["intro"]) + list(case.get("events") or [])
    return {"id": name, **{k: v for k, v in case.items() if k != "events"}, "events": events}


def play(name: str, tool: BookingTool | None = None):
    return PolicyHarness.from_flow_path(FLOW, tool=tool or BookingTool()).replay(load_fixture(name))


def rules(result) -> set[str]:
    return {item.rule for item in result.violations}


class BookingRuleTests(unittest.TestCase):
    def test_happy_path_books_once_and_sends_sms_after_consent(self):
        tool = BookingTool()
        result = play("happy_path_book_and_sms", tool)
        self.assertTrue(result.ok, result.violations)
        self.assertEqual(result.bookings_created, ["bk_sample_001"])
        self.assertEqual(result.sms_sent, 1)
        self.assertEqual(len(tool.bookings()), 1)
        self.assertEqual(tool.sms_log[0]["phone"], "555-0100")

    def test_no_confirm_when_booking_tool_fails(self):
        result = play("tool_failure_no_confirm")
        self.assertTrue(result.ok, result.violations)
        self.assertEqual(result.bookings_created, [])

    def test_harness_flags_confirm_without_tool_success(self):
        result = play("confirm_without_success")
        self.assertFalse(result.ok)
        self.assertEqual(rules(result), {RULE_CONFIRM})

    def test_repeated_call_does_not_create_a_duplicate_booking(self):
        tool = BookingTool()
        harness = PolicyHarness.from_flow_path(FLOW, tool=tool)
        first = harness.replay(load_fixture("happy_path_book_and_sms"))
        second = harness.replay(load_fixture("repeat_same_details"))
        self.assertTrue(first.ok, first.violations)
        self.assertTrue(second.ok, second.violations)
        self.assertEqual(first.bookings_created, ["bk_sample_001"])
        self.assertEqual(second.bookings_created, [])
        self.assertEqual(len(tool.bookings()), 1)
        results = [ev["result"] for ev in second.events if ev.get("tool") == "create_booking"]
        self.assertEqual(results[0]["reason"], "duplicate")
        self.assertFalse(results[0]["ok"])

    def test_declined_caller_is_not_booked(self):
        tool = BookingTool()
        result = play("caller_declines", tool)
        self.assertTrue(result.ok, result.violations)
        self.assertEqual(result.bookings_created, [])
        self.assertEqual(tool.bookings(), [])

    def test_harness_flags_booking_after_decline(self):
        result = play("book_after_decline")
        self.assertFalse(result.ok)
        self.assertIn(RULE_DECLINE, rules(result))

    def test_harness_flags_sms_without_consent(self):
        result = play("sms_without_consent")
        self.assertFalse(result.ok)
        self.assertEqual(rules(result), {RULE_SMS})
        self.assertEqual(result.sms_sent, 0)

    def test_webhook_example_matches_mock_payload_shape(self):
        tool = BookingTool()
        result = play("happy_path_book_and_sms", tool)
        generated = tool.webhook_payload(result.bookings_created[0])
        self.assertEqual(generated["event"], EXAMPLE["event"])
        self.assertEqual(generated["booking"]["phone"], "555-0100")
        self.assertEqual(generated["booking"]["booking_id"], EXAMPLE["booking"]["booking_id"])
        self.assertIsNone(re.search(r"https?://", json.dumps(EXAMPLE)))


if __name__ == "__main__":
    unittest.main()
