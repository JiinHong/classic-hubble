from __future__ import annotations

import importlib
import io
import json
from datetime import date

from classic_hubble_pipeline.kopis import KopisPerformanceSummary
from classic_hubble_pipeline.nol import NolPerformanceData, NolProgramItem


def _load_cli_module():
    return importlib.import_module("classic_hubble_pipeline.cli")


def test_kopis_check_reports_missing_api_key_without_starting_a_request():
    cli = _load_cli_module()
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = cli.main(
        [
            "kopis-check",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-31",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "KOPIS_API_KEY" in stderr.getvalue()


def test_kopis_check_prints_a_small_json_snapshot():
    cli = _load_cli_module()
    captured: dict[str, object] = {}
    stdout = io.StringIO()
    stderr = io.StringIO()

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def list_performances(self, window, *, rows):
            captured["window"] = window
            captured["rows"] = rows
            return (
                KopisPerformanceSummary(
                    performance_id="PF300001",
                    title="라흐마니노프 피아노 협주곡 2번",
                    start_date=date(2026, 7, 18),
                    end_date=date(2026, 7, 18),
                    facility_name="예술의전당 콘서트홀",
                    poster_url="https://kopis.or.kr/posters/PF300001.jpg",
                    area="서울특별시",
                    genre_name="서양음악(클래식)",
                    open_run=False,
                    state="공연예정",
                    raw_payload={"mt20id": "PF300001"},
                ),
            )

    def client_factory(settings):
        captured["settings"] = settings
        return FakeClient()

    exit_code = cli.main(
        [
            "kopis-check",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-31",
            "--rows",
            "5",
        ],
        environ={"KOPIS_API_KEY": "test-key"},
        stdout=stdout,
        stderr=stderr,
        client_factory=client_factory,
    )

    payload = json.loads(stdout.getvalue())
    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert payload == {
        "count": 1,
        "performances": [
            {
                "performance_id": "PF300001",
                "title": "라흐마니노프 피아노 협주곡 2번",
                "start_date": "2026-07-18",
                "end_date": "2026-07-18",
                "facility_name": "예술의전당 콘서트홀",
                "state": "공연예정",
            }
        ],
    }
    assert captured["rows"] == 5
    assert captured["window"].genre_code == "CCCA"


def test_kopis_sync_reports_missing_supabase_secret_before_opening_clients():
    cli = _load_cli_module()
    stdout = io.StringIO()
    stderr = io.StringIO()

    def unexpected_client_factory(settings):
        raise AssertionError("KOPIS client must not be opened")

    exit_code = cli.main(
        [
            "kopis-sync",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-31",
        ],
        environ={
            "KOPIS_API_KEY": "test-key",
            "SUPABASE_URL": "https://project-ref.supabase.co",
        },
        stdout=stdout,
        stderr=stderr,
        client_factory=unexpected_client_factory,
    )

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert "SUPABASE_SECRET_KEY" in stderr.getvalue()


def test_kopis_sync_prints_the_completed_run_summary():
    cli = _load_cli_module()
    captured: dict[str, object] = {}
    stdout = io.StringIO()
    stderr = io.StringIO()

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def iter_performances(self, window, *, rows):
            captured["window"] = window
            captured["rows"] = rows
            return iter(())

    class FakeRepository:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def start_ingestion_run(self, provider):
            captured["provider"] = provider
            return "run-1"

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            captured["finished"] = (run_id, status, counters, error)

    def client_factory(settings):
        captured["kopis_settings"] = settings
        return FakeClient()

    def repository_factory(settings):
        captured["supabase_settings"] = settings
        return FakeRepository()

    exit_code = cli.main(
        [
            "kopis-sync",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-31",
            "--rows",
            "25",
        ],
        environ={
            "KOPIS_API_KEY": "test-key",
            "SUPABASE_URL": "https://project-ref.supabase.co",
            "SUPABASE_SECRET_KEY": "sb_secret_test",
        },
        stdout=stdout,
        stderr=stderr,
        client_factory=client_factory,
        repository_factory=repository_factory,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert json.loads(stdout.getvalue()) == {
        "run_id": "run-1",
        "status": "completed",
        "counters": {
            "performance_summaries": 0,
            "performance_details": 0,
            "facilities": 0,
            "halls": 0,
            "performances": 0,
            "review_items": 0,
            "nol_records": 0,
            "program_items": 0,
            "nol_errors": 0,
        },
    }
    assert captured["provider"] == "kopis"
    assert captured["rows"] == 25


def test_nol_check_prints_a_safe_deterministic_snapshot_without_credentials():
    cli = _load_cli_module()
    captured: dict[str, object] = {}
    stdout = io.StringIO()
    stderr = io.StringIO()

    class FakeNolClient:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def fetch(self, url):
            captured["url"] = url
            return NolPerformanceData(
                goods_code="26007299",
                title="조성음 귀국 바이올린 독주회",
                venue_name="금호아트홀 연세",
                program_status="confirmed",
                program_source_url="https://tickets.interpark.com/goods/26007299",
                program_image_urls=(
                    "https://ticketimage.interpark.com/Play/program.jpg",
                ),
                program_items=(
                    NolProgramItem(
                        position=0,
                        display_title=(
                            "W. A. Mozart (1756-1791)\n"
                            "Violin Sonata No. 18 in G Major, K. 301"
                        ),
                        composer="W. A. Mozart",
                        composer_lifespan="1756-1791",
                        work_title="Violin Sonata No. 18 in G Major, K. 301",
                    ),
                ),
                raw_summary={"large": "raw payload is intentionally omitted"},
                raw_play_db={"data": {"programInfo": "raw"}},
            )

    def nol_client_factory(settings):
        captured["settings"] = settings
        return FakeNolClient()

    exit_code = cli.main(
        [
            "nol-check",
            "--url",
            "https://tickets.interpark.com/goods/26007299",
        ],
        environ={},
        stdout=stdout,
        stderr=stderr,
        nol_client_factory=nol_client_factory,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert captured["url"] == "https://tickets.interpark.com/goods/26007299"
    assert json.loads(stdout.getvalue()) == {
        "goods_code": "26007299",
        "title": "조성음 귀국 바이올린 독주회",
        "venue_name": "금호아트홀 연세",
        "program_status": "confirmed",
        "program_source_url": "https://tickets.interpark.com/goods/26007299",
        "program_image_urls": [
            "https://ticketimage.interpark.com/Play/program.jpg"
        ],
        "program_items": [
            {
                "position": 0,
                "display_title": (
                    "W. A. Mozart (1756-1791)\n"
                    "Violin Sonata No. 18 in G Major, K. 301"
                ),
                "composer": "W. A. Mozart",
                "composer_lifespan": "1756-1791",
                "work_title": "Violin Sonata No. 18 in G Major, K. 301",
            }
        ],
    }
    assert "raw payload" not in stdout.getvalue()


def test_kopis_sync_opens_nol_client_only_when_enrichment_is_enabled():
    cli = _load_cli_module()
    captured: dict[str, object] = {}
    stdout = io.StringIO()
    stderr = io.StringIO()

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def iter_performances(self, window, *, rows):
            return iter(())

    class FakeNolClient:
        def __enter__(self):
            captured["nol_entered"] = True
            return self

        def __exit__(self, *args: object) -> None:
            pass

    class FakeRepository:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            pass

        def start_ingestion_run(self, provider):
            return "run-1"

        def finish_ingestion_run(self, run_id, *, status, counters, error=None):
            pass

    def nol_client_factory(settings):
        captured["nol_settings"] = settings
        return FakeNolClient()

    exit_code = cli.main(
        [
            "kopis-sync",
            "--start",
            "2026-07-01",
            "--end",
            "2026-07-31",
            "--enrich-nol",
        ],
        environ={
            "KOPIS_API_KEY": "test-key",
            "SUPABASE_URL": "https://project-ref.supabase.co",
            "SUPABASE_SECRET_KEY": "sb_secret_test",
            "NOL_TIMEOUT_SECONDS": "7",
        },
        stdout=stdout,
        stderr=stderr,
        client_factory=lambda settings: FakeClient(),
        repository_factory=lambda settings: FakeRepository(),
        nol_client_factory=nol_client_factory,
    )

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert captured["nol_entered"] is True
    assert captured["nol_settings"].timeout_seconds == 7
