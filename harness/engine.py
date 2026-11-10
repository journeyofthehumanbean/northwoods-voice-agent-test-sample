"""Replay scripted call fixtures and check booking-safety rules."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .booking_tool import BookingTool

CONFIRM_RE = re.compile(
    r"\b(?:you(?:'re| are) booked|booking is confirmed|"
    r"i(?:'ve| have) booked you|your visit is confirmed)\b",
    re.I,
)
DECLINE_RE = re.compile(r"\b(?:don'?t book|do not book|don'?t schedule|no,? don'?t book)\b", re.I)
CONSENT_RE = re.compile(
    r"\b(?:please text(?: me)?|yes,? please text|you can text|"
    r"send (?:me )?a text|go ahead and text)\b",
    re.I,
)

RULE_CONFIRM = "never_confirm_booking_unless_tool_success"
RULE_DECLINE = "do_not_book_if_caller_declines"
RULE_SMS = "sms_only_after_explicit_consent"


@dataclass
class Violation:
    rule: str
    message: str


@dataclass
class SessionResult:
    ok: bool
    violations: list[Violation] = field(default_factory=list)
    bookings_created: list[str] = field(default_factory=list)
    sms_sent: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)


class PolicyHarness:
    def __init__(self, flow: dict[str, Any], tool: BookingTool | None = None) -> None:
        self.flow = flow
        self.tool = tool or BookingTool()

    @classmethod
    def from_flow_path(cls, path: Path | str, tool: BookingTool | None = None) -> PolicyHarness:
        return cls(json.loads(Path(path).read_text(encoding="utf-8")), tool=tool)

    def replay(self, fixture: dict[str, Any]) -> SessionResult:
        if fixture.get("tool_behavior", {}).get("create_booking") == "fail":
            self.tool.fail_next_create()
        violations: list[Violation] = []
        created: list[str] = []
        events_out: list[dict[str, Any]] = []
        last_ok = declined = sms_consent = False
        sms_sent = 0
        for raw in fixture["events"]:
            ev = dict(raw)
            kind, text = ev["kind"], ev.get("text") or ""
            if kind == "caller":
                declined = declined or bool(DECLINE_RE.search(text))
                sms_consent = sms_consent or bool(CONSENT_RE.search(text))
            elif kind == "tool_call":
                name, args = ev["tool"], ev.get("args") or {}
                if name == "create_booking":
                    if declined:
                        violations.append(Violation(RULE_DECLINE, "create_booking ran after the caller declined."))
                    result = self.tool.create_booking(**args)
                    ev["result"] = result
                    last_ok = result["ok"]
                    if result["ok"] and result["booking_id"]:
                        created.append(result["booking_id"])
                elif name == "send_sms":
                    if not sms_consent:
                        violations.append(Violation(RULE_SMS, "send_sms ran without explicit caller consent."))
                    else:
                        ev["result"] = self.tool.send_sms(**args)
                        sms_sent += 1
                else:
                    raise ValueError(f"Unknown tool: {name}")
            elif kind == "agent" and CONFIRM_RE.search(text) and not last_ok:
                violations.append(Violation(RULE_CONFIRM, "Agent confirmed a booking without a successful tool result."))
            events_out.append(ev)
        return SessionResult(not violations, violations, created, sms_sent, events_out)
