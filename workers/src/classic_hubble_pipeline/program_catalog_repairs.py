"""Additive, source-backed corrections to catalogue identities used by NOL."""

from uuid import NAMESPACE_URL, uuid5

from .work_matching import _normalize


def build_repair_plan(manifest, works, composers):
    by_slug = {w["slug"]: w for w in works}
    names = {_normalize(c["name"]): c["id"] for c in composers}
    plan = {"new_works": [], "updates": [], "aliases": [], "provenance": []}
    for repair in manifest["repairs"]:
        if not repair.get("source_url", "").startswith("https://"):
            raise ValueError("A catalogue repair needs a source URL")
        composer_id = names.get(_normalize(repair["composer"]))
        if not composer_id:
            raise ValueError("Unknown composer")
        work = by_slug.get(repair["slug"])
        if work and work["composer_id"] != composer_id:
            raise ValueError("Work composer changed")
        if not work:
            if not repair.get("new"):
                raise ValueError("Expected existing work is missing")
            if any(
                w["composer_id"] == composer_id
                and (
                    _normalize(w["title"]) == _normalize(repair["title"])
                    or (
                        repair.get("catalogue")
                        and w.get("catalogue") == repair["catalogue"]
                    )
                )
                for w in works
            ):
                raise ValueError(
                    "Possible duplicate work requires identity reconciliation"
                )
            work = {
                "id": str(
                    uuid5(
                        NAMESPACE_URL,
                        "https://classichubble.com/works/" + repair["slug"],
                    )
                ),
                "slug": repair["slug"],
                "composer_id": composer_id,
                "title": repair["title"],
                "title_ko": repair.get("title_ko"),
                "catalogue": repair.get("catalogue"),
            }
            plan["new_works"].append(work)
        elif "catalogue" in repair and work["catalogue"] != repair["catalogue"]:
            if work["catalogue"] != repair.get("expected_catalogue"):
                raise ValueError("Work catalogue changed")
            plan["updates"].append(
                {
                    "id": work["id"],
                    "composer_id": composer_id,
                    "expected_catalogue": work["catalogue"],
                    "catalogue": repair["catalogue"],
                }
            )
        for alias in repair["aliases"]:
            plan["aliases"].append(
                {
                    "work_id": work["id"],
                    "alias": alias,
                    "locale": "en",
                    "source": "verified:" + repair["source_url"],
                }
            )
        plan["provenance"].append(
            {
                "provider": "catalogue_repair",
                "entity_type": "canonical_work",
                "provider_id": repair["slug"],
                "payload": {**repair, "work_id": work["id"]},
            }
        )
    return plan


def apply_repair_plan(repository, plan):
    for change in plan["updates"]:
        rows = repository._request(
            "PATCH",
            "works",
            params={
                "id": "eq." + change["id"],
                "composer_id": "eq." + change["composer_id"],
                "catalogue": "is.null"
                if change["expected_catalogue"] is None
                else "eq." + change["expected_catalogue"],
            },
            json={"catalogue": change["catalogue"]},
            prefer="return=representation",
        ).json()
        if len(rows) != 1:
            raise ValueError("Catalogue changed since the repair was planned")
    for table, rows, conflict in (
        ("works", plan["new_works"], "id"),
        ("work_aliases", plan["aliases"], "work_id,alias"),
        ("provider_records", plan["provenance"], "provider,entity_type,provider_id"),
    ):
        if rows:
            repository._request(
                "POST",
                table,
                params={"on_conflict": conflict},
                json=rows,
                prefer="resolution=ignore-duplicates,return=minimal",
            )
