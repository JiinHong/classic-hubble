from pathlib import Path


def test_daily_workflow_enables_recovery_and_reports_each_provider_outcome():
    workflow = (Path(__file__).parents[2] / ".github/workflows/daily-ingestion.yml").read_text()
    assert workflow.count("--recover-source-errors") == 2
    assert "id: catalog" in workflow
    assert "id: nol" in workflow
    assert "${{ steps.catalog.outcome }}" in workflow
    assert "${{ steps.nol.outcome }}" in workflow
    assert "continue-on-error: true" not in workflow
