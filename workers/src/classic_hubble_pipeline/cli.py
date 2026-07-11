from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, ExitStack
from datetime import date
from typing import TextIO

from dotenv import load_dotenv

from .kopis import (
    KopisClient,
    KopisConfigurationError,
    KopisError,
    KopisPerformanceSummary,
    KopisSettings,
    KopisSyncWindow,
)
from .kopis_sync import KopisSyncService
from .nol import (
    NolClient,
    NolConfigurationError,
    NolError,
    NolPerformanceData,
    NolSettings,
)
from .supabase import (
    SupabaseConfigurationError,
    SupabaseError,
    SupabaseRepository,
    SupabaseSettings,
)


ClientFactory = Callable[[KopisSettings], AbstractContextManager[KopisClient]]
RepositoryFactory = Callable[
    [SupabaseSettings], AbstractContextManager[SupabaseRepository]
]
NolClientFactory = Callable[[NolSettings], AbstractContextManager[NolClient]]


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    client_factory: ClientFactory = KopisClient,
    repository_factory: RepositoryFactory = SupabaseRepository,
    nol_client_factory: NolClientFactory = NolClient,
) -> int:
    output = sys.stdout if stdout is None else stdout
    errors = sys.stderr if stderr is None else stderr
    args = _build_parser().parse_args(argv)

    if environ is None:
        load_dotenv()

    if args.command == "kopis-check":
        return _run_check(
            args,
            environ=environ,
            output=output,
            errors=errors,
            client_factory=client_factory,
        )
    if args.command == "nol-check":
        return _run_nol_check(
            args,
            environ=environ,
            output=output,
            errors=errors,
            nol_client_factory=nol_client_factory,
        )
    return _run_sync(
        args,
        environ=environ,
        output=output,
        errors=errors,
        client_factory=client_factory,
        repository_factory=repository_factory,
        nol_client_factory=nol_client_factory,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="classic-hubble-pipeline")
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser(
        "kopis-check",
        help="Fetch and print one page of classical performances from KOPIS.",
    )
    check.add_argument("--start", required=True, type=date.fromisoformat)
    check.add_argument("--end", required=True, type=date.fromisoformat)
    check.add_argument("--rows", type=int, default=10)

    nol_check = subcommands.add_parser(
        "nol-check",
        help="Fetch and print deterministic program data from one NOL goods URL.",
    )
    nol_check.add_argument("--url", required=True)

    sync = subcommands.add_parser(
        "kopis-sync",
        help="Synchronize classical performances and facilities into Supabase.",
    )
    sync.add_argument("--start", required=True, type=date.fromisoformat)
    sync.add_argument("--end", required=True, type=date.fromisoformat)
    sync.add_argument("--rows", type=int, default=100)
    sync.add_argument("--limit", type=int)
    sync.add_argument(
        "--enrich-nol",
        action="store_true",
        help="Enrich KOPIS records from official NOL goods pages.",
    )
    return parser


def _run_nol_check(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None,
    output: TextIO,
    errors: TextIO,
    nol_client_factory: NolClientFactory,
) -> int:
    try:
        settings = NolSettings.from_env(environ)
        with nol_client_factory(settings) as client:
            performance = client.fetch(args.url)
    except (NolConfigurationError, ValueError) as error:
        errors.write(f"Configuration error: {error}\n")
        return 2
    except NolError as error:
        errors.write(f"NOL check failed: {error}\n")
        return 1

    _write_json(_nol_payload(performance), output)
    return 0


def _run_check(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None,
    output: TextIO,
    errors: TextIO,
    client_factory: ClientFactory,
) -> int:
    try:
        settings = KopisSettings.from_env(environ)
        window = KopisSyncWindow(args.start, args.end)
        with client_factory(settings) as client:
            performances = client.list_performances(window, rows=args.rows)
    except (KopisConfigurationError, ValueError) as error:
        errors.write(f"Configuration error: {error}\n")
        return 2
    except KopisError as error:
        errors.write(f"KOPIS check failed: {error}\n")
        return 1

    _write_json(
        {
            "count": len(performances),
            "performances": [_summary_payload(item) for item in performances],
        },
        output,
    )
    return 0


def _run_sync(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None,
    output: TextIO,
    errors: TextIO,
    client_factory: ClientFactory,
    repository_factory: RepositoryFactory,
    nol_client_factory: NolClientFactory,
) -> int:
    try:
        kopis_settings = KopisSettings.from_env(environ)
        supabase_settings = SupabaseSettings.from_env(environ)
        with ExitStack() as stack:
            client = stack.enter_context(client_factory(kopis_settings))
            repository = stack.enter_context(repository_factory(supabase_settings))
            nol_client = None
            if args.enrich_nol:
                nol_settings = NolSettings.from_env(environ)
                nol_client = stack.enter_context(nol_client_factory(nol_settings))
            result = KopisSyncService(
                client,
                repository,
                nol_client=nol_client,
            ).run(
                start_date=args.start,
                end_date=args.end,
                rows=args.rows,
                limit=args.limit,
            )
    except (
        KopisConfigurationError,
        NolConfigurationError,
        SupabaseConfigurationError,
        ValueError,
    ) as error:
        errors.write(f"Configuration error: {error}\n")
        return 2
    except (KopisError, NolError, SupabaseError) as error:
        errors.write(f"KOPIS sync failed: {error}\n")
        return 1

    _write_json(
        {
            "run_id": result.run_id,
            "status": result.status,
            "counters": result.counters,
        },
        output,
    )
    return 0


def _write_json(payload: Mapping[str, object], output: TextIO) -> None:
    json.dump(payload, output, ensure_ascii=False, indent=2)
    output.write("\n")


def _summary_payload(item: KopisPerformanceSummary) -> dict[str, object]:
    return {
        "performance_id": item.performance_id,
        "title": item.title,
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
        "facility_name": item.facility_name,
        "state": item.state,
    }


def _nol_payload(item: NolPerformanceData) -> dict[str, object]:
    return {
        "goods_code": item.goods_code,
        "title": item.title,
        "venue_name": item.venue_name,
        "program_status": item.program_status,
        "program_source_url": item.program_source_url,
        "program_image_urls": list(item.program_image_urls),
        "program_items": [
            {
                "position": program.position,
                "display_title": program.display_title,
                "composer": program.composer,
                "composer_lifespan": program.composer_lifespan,
                "work_title": program.work_title,
            }
            for program in item.program_items
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
