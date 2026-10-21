from __future__ import annotations

from typing import Protocol, Any

from .work_matching import CanonicalWork, match_work


class MatchingRepository(Protocol):
    def load_work_catalog(self) -> list[CanonicalWork]: ...
    def load_unlinked_program_items(self) -> list[dict[str, Any]]: ...
    def link_program_item(self, item: dict[str, Any], work_id: str) -> bool: ...


def match_stored_programs(
    repository: MatchingRepository, *, apply: bool = False
) -> dict[str, Any]:
    works = repository.load_work_catalog()
    items = repository.load_unlinked_program_items()
    results = []
    matched = updated = 0
    for item in items:
        result = match_work(item["display_title"], item["composer_name"], works)
        if result.work_id:
            matched += 1
            if apply and repository.link_program_item(item, result.work_id):
                updated += 1
        results.append(
            {
                "program_item_id": item["id"],
                "title": item["display_title"],
                "source_url": item.get("source_url"),
                "work_id": result.work_id,
                "candidate_ids": result.candidate_ids,
                "reason": result.reason,
            }
        )
    return {
        "mode": "apply" if apply else "dry_run",
        "catalogue_size": len(works),
        "scanned": len(items),
        "matched": matched,
        "updated": updated,
        "unresolved": len(items) - matched,
        "items": results,
    }
