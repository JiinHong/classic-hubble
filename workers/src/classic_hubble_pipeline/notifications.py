from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationCandidate:
    user_id: str
    work_slug: str
    performance_id: str
    channel: str


def should_send_notification(candidate: NotificationCandidate, confidence: float) -> bool:
    return candidate.channel in {"email", "web_push"} and confidence >= 0.85
