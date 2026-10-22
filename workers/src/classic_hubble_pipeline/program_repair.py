"""Plan source-preserving, compare-and-swap replacements for NOL programs."""

from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from .program_split import VERSION, split_program_block

FIELDS = (
    "id",
    "display_title",
    "composer_name",
    "work_id",
    "source_type",
    "confidence",
    "position",
    "source_url",
)


def plan_program_repairs(rows, matcher, target_ids):
    grouped = defaultdict(list)
    for row in rows:
        if row["source_provider"] == "nol":
            grouped[row["performance_id"]].append(row)
    plans = []
    for performance_id, original in sorted(grouped.items()):
        original.sort(key=lambda r: (r["position"], r["id"]))
        if not any(r["id"] in target_ids and not r.get("work_id") for r in original):
            continue
        items, outcomes = [], []
        for row in original:
            base = {k: row.get(k) for k in FIELDS}
            if row["id"] not in target_ids or row.get("work_id"):
                items.append(base)
                continue
            segments = split_program_block(row, matcher)
            outcomes.append(
                {"program_item_id": row["id"], "source": row, "segments": segments}
            )
            for i, segment in enumerate(segments):
                items.append(
                    {
                        **base,
                        **{
                            k: segment[k]
                            for k in ("display_title", "composer_name", "work_id")
                        },
                        "id": row["id"]
                        if i == 0
                        else str(uuid5(NAMESPACE_URL, f"{VERSION}:{row['id']}:{i}")),
                    }
                )
        for position, item in enumerate(items):
            item["position"] = position
        if items != [{k: r.get(k) for k in FIELDS} for r in original]:
            plans.append(
                {
                    "performance_id": performance_id,
                    "expected": original,
                    "items": items,
                    "outcomes": outcomes,
                }
            )
    return plans
