from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationCandidate:
    user_id: str
    work_slug: str
    performance_id: str
    channel: str


def should_send_notification(
    candidate: NotificationCandidate, confidence: float, *, email_enabled: bool
) -> bool:
    return candidate.channel == "email" and email_enabled and confidence >= 0.85
