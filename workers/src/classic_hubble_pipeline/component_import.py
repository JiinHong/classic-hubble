"""Explicit, additive deployment of reviewed component-inventory decisions."""

import argparse
import json
from pathlib import Path

from dotenv import dotenv_values

from .catalog_import import digest
from .r2 import R2Settings, R2Store
from .supabase import SupabaseRepository, SupabaseSettings
from .work_components import apply_component_plan, build_component_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-ref", required=True)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if (
        digest({k: v for k, v in manifest.items() if k != "sha256"})
        != manifest["sha256"]
    ):
        raise ValueError("Component inventory integrity mismatch")
    env = dotenv_values(args.env_file)
    settings = SupabaseSettings.from_env(env)
    if settings.url != f"https://{args.project_ref}.supabase.co":
        raise ValueError("Unexpected Supabase project")
    with SupabaseRepository(settings) as repository:
        works = repository._read_pages(
            "works",
            {"select": "id,slug,composer_id,title,title_ko,catalogue,instrumentation"},
            page_size=1000,
        )
        aliases = repository._read_pages(
            "work_aliases", {"select": "work_id,alias"}, page_size=1000
        )
        records = repository._read_pages(
            "provider_records",
            {
                "select": "payload",
                "provider": "eq.classic_hubble",
                "entity_type": "eq.work_component",
            },
            page_size=1000,
        )
        relations = list(
            {
                (
                    r["payload"]["relation"]["parent_slug"],
                    r["payload"]["relation"]["child_slug"],
                ): r["payload"]["relation"]
                for r in records
            }.values()
        )
        plan = build_component_plan(manifest["observations"], works, aliases, relations)
        if plan["held"]:
            raise ValueError("Live identity drift: component import needs a new audit")
        report = {
            "manifest_sha256": manifest["sha256"],
            "target": settings.url,
            "apply": args.apply,
            "status": "planned",
            "counts": {k: len(v) for k, v in plan.items()},
            "plan": plan,
        }
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        if args.apply:
            with R2Store(R2Settings.from_env(env)) as store:
                saved = store.archive_catalog_snapshot(manifest)
                if json.loads(store.read(saved.key)) != manifest:
                    raise ValueError("Component archive readback mismatch")
                report["archive"] = {"key": saved.key, "sha256": saved.sha256}
            apply_component_plan(repository, plan, apply=True)
            report["status"] = "applied"
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(json.dumps({k: report[k] for k in ("target", "status", "counts")}))


if __name__ == "__main__":
    main()
