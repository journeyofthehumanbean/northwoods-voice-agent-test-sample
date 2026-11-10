"""In-memory booking tool and SMS log. Sample data only; no network calls."""

from __future__ import annotations

from typing import Any


class BookingTool:
    """Fake booking backend with idempotency on (phone, slot, service)."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], dict[str, Any]] = {}
        self._fail_next_create = False
        self.sms_log: list[dict[str, str]] = []

    def fail_next_create(self) -> None:
        self._fail_next_create = True

    def create_booking(
        self, customer_name: str, phone: str, service: str, preferred_slot: str
    ) -> dict[str, Any]:
        if self._fail_next_create:
            self._fail_next_create = False
            return {"ok": False, "booking_id": None, "reason": "service_unavailable"}
        key = (phone, preferred_slot, service)
        existing = self._records.get(key)
        if existing:
            return {"ok": False, "booking_id": existing["booking_id"], "reason": "duplicate"}
        booking_id = f"bk_sample_{len(self._records) + 1:03d}"
        self._records[key] = {
            "booking_id": booking_id,
            "customer_name": customer_name,
            "phone": phone,
            "service": service,
            "preferred_slot": preferred_slot,
        }
        return {"ok": True, "booking_id": booking_id, "reason": None}

    def send_sms(self, phone: str, message: str) -> dict[str, Any]:
        self.sms_log.append({"phone": phone, "message": message})
        return {"ok": True}

    def bookings(self) -> list[dict[str, Any]]:
        return list(self._records.values())

    def webhook_payload(self, booking_id: str) -> dict[str, Any]:
        """Return a Make-style webhook body for a stored booking. No URL."""
        record = next(item for item in self._records.values() if item["booking_id"] == booking_id)
        return {
            "event": "booking.created",
            "source": "sample-voice-agent",
            "company": "Example Plumbing Co",
            "booking": {**record, "sms_consent": True},
            "note": "Sample payload only. There is no live webhook endpoint in this repo.",
        }
