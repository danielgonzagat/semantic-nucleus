import json
from datetime import datetime, timezone

from metanucleus.evolution.report import write_auto_evolve_report
from metanucleus.evolution.types import EvolutionPatch
from metanucleus.kernel.meta_kernel import AutoEvolutionFilters


def test_write_auto_evolve_report(tmp_path):
    patches = [
        EvolutionPatch(
            domain="intent",
            title="Atualizar intenção",
            description="Nova regra",
            diff="--- a\n+++ b\n",
            meta={"count": 1},
        )
    ]
    stats = [{"domain": "intent", "status": "executed", "entries_scanned": 3}]
    filters = AutoEvolutionFilters(
        log_since=datetime(2025, 1, 1, tzinfo=timezone.utc),
        frame_languages={"pt", "en"},
    )
    output = tmp_path / "report.json"

    write_auto_evolve_report(
        output,
        domains=["intent", "rules"],
        patches=patches,
        domain_stats=stats,
        filters=filters,
        applied=False,
        source="test-suite",
        max_patches=5,
    )

    payload = json.loads(output.read_text())
    assert payload["patch_count"] == 1
    assert payload["domains"] == ["intent", "rules"]
    assert payload["filters"]["frame_languages"] == ["en", "pt"]
    assert payload["filters"]["log_since"].startswith("2025")
    assert payload["patches"][0]["domain"] == "intent"
    assert payload["patches"][0]["applied"] is False
