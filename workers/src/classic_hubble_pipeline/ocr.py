from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PosterExtraction:
    image_url: str
    extracted_text: str
    provider: str
    confidence: float


def queue_poster_extraction(image_url: str) -> PosterExtraction:
    return PosterExtraction(
        image_url=image_url,
        extracted_text="",
        provider="pending",
        confidence=0.0,
    )
