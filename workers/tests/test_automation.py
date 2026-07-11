from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = PROJECT_ROOT / ".github" / "workflows"


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_ci_runs_every_project_verification_command() -> None:
    workflow = _workflow("ci.yml")

    assert "pnpm install --frozen-lockfile" in workflow
    assert "pnpm test" in workflow
    assert "pnpm lint" in workflow
    assert "pnpm build" in workflow
    assert "python -m pytest workers/tests" in workflow


def test_daily_ingestion_runs_after_kopis_refresh_and_before_nol_peak() -> None:
    workflow = _workflow("daily-ingestion.yml")

    assert 'cron: "27 16 * * *"' in workflow
    assert 'timezone: "Asia/Seoul"' in workflow
    assert "workflow_dispatch:" in workflow


def test_daily_ingestion_uses_repository_secrets_without_loading_env_files() -> None:
    workflow = _workflow("daily-ingestion.yml")

    assert "KOPIS_API_KEY: ${{ secrets.KOPIS_API_KEY }}" in workflow
    assert "SUPABASE_URL: ${{ secrets.SUPABASE_URL }}" in workflow
    assert "SUPABASE_SECRET_KEY: ${{ secrets.SUPABASE_SECRET_KEY }}" in workflow
    assert "source .env" not in workflow


def test_daily_ingestion_limits_nol_enrichment_to_near_term_performances() -> None:
    workflow = _workflow("daily-ingestion.yml")

    assert "180 days" in workflow
    assert "31 days" in workflow
    assert "--enrich-nol" in workflow
    assert "--limit" in workflow


def test_daily_ingestion_prevents_overlapping_runs() -> None:
    workflow = _workflow("daily-ingestion.yml")

    assert "concurrency:" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
