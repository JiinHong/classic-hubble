from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkAlias:
    work_slug: str
    aliases: tuple[str, ...]


ALIASES: tuple[WorkAlias, ...] = (
    WorkAlias(
        work_slug="rachmaninoff-piano-concerto-2",
        aliases=(
            "라흐 피협 2번",
            "라흐마니노프 피아노 협주곡 2번",
            "라피협 2",
            "rachmaninoff piano concerto no 2",
            "piano concerto no 2 op 18",
        ),
    ),
    WorkAlias(
        work_slug="beethoven-symphony-5",
        aliases=(
            "운명",
            "베토벤 교향곡 5번",
            "beethoven symphony no 5",
            "fate symphony",
        ),
    ),
    WorkAlias(
        work_slug="dvorak-symphony-9",
        aliases=(
            "신세계",
            "드보르자크 신세계",
            "dvorak symphony no 9",
            "from the new world",
        ),
    ),
)


def _normalize(value: str) -> str:
    lowered = value.lower()
    stripped = re.sub(r"[.,:;'\"“”‘’〈〉<>()\[\]\-]", " ", lowered)
    return re.sub(r"\s+", " ", stripped).strip()


def normalize_work_candidate(raw_title: str) -> dict[str, object]:
    normalized = _normalize(raw_title)
    best_slug: str | None = None
    best_score = 0.0

    for work_alias in ALIASES:
        for alias in work_alias.aliases:
            normalized_alias = _normalize(alias)
            if normalized == normalized_alias:
                score = 0.96
            elif normalized_alias in normalized or normalized in normalized_alias:
                score = 0.84
            else:
                alias_tokens = set(normalized_alias.split())
                title_tokens = set(normalized.split())
                score = len(alias_tokens & title_tokens) / max(len(alias_tokens), 1)

            if score > best_score:
                best_score = score
                best_slug = work_alias.work_slug

    if best_score < 0.55:
        return {
            "work_slug": None,
            "confidence": round(best_score, 2),
            "review_required": True,
            "normalized_input": normalized,
        }

    return {
        "work_slug": best_slug,
        "confidence": round(best_score, 2),
        "review_required": best_score < 0.85,
        "normalized_input": normalized,
    }
