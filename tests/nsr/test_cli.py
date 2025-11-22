import json

import nsr.cli as nsr_cli


def test_cli_outputs_equation_bundle(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--enable-contradictions"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    assert data["answer"]
    assert "equation" in data
    assert "json" in data["equation"]
    assert data["equation"]["json"]["answer"]["kind"] == "STRUCT"
    assert data["equation"]["json"]["ontology"]
    assert "ops_queue" in data["equation"]["json"]
    assert isinstance(data["equation"]["json"]["quality"], float)
    assert len(data["equation_hash"]) == 32
    assert data["invariant_failures"] == []


def test_cli_supports_plan_only_mode(capsys):
    exit_code = nsr_cli.main(["2 + 2", "--include-calc", "--calc-mode", "plan_only"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    assert data["halt_reason"] == "PLAN_EXECUTED"
    calc = data.get("meta_calc")
    assert calc is not None
    assert calc["consistent"] is True
    assert calc["error"] is None

def test_cli_writes_file(tmp_path):
    output_path = tmp_path / "bundle.json"
    exit_code = nsr_cli.main(
        [
            "O carro tem roda",
            "--disable-contradictions",
            "--format",
            "both",
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output_path.read_text())
    assert payload["equation"]["sexpr"]["input"].startswith("(STRUCT")
    assert payload["trace_digest"]
    assert payload["equation_hash"]
    assert payload["equation"]["json"]["goals"]
    assert "ops_queue" in payload["equation"]["json"]


def test_cli_includes_text_report(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--include-report"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    assert "equation_report" in data
    assert "FilaΦ" in data["equation_report"]


def test_cli_includes_stats(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--include-stats"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    assert "equation_stats" in data
    assert data["equation_stats"]["ontology"]["count"] >= 0
    assert len(data["equation_stats"]["input_digest"]) == 32
    assert "invariant_failures" in data


def test_cli_includes_explanation(capsys):
    exit_code = nsr_cli.main(["O carro tem roda", "--format", "json", "--include-explanation"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    assert "explanation" in data
    assert "Explicação determinística" in data["explanation"]
    assert "Relações" in data["explanation"]
    assert "Relações novas" in data["explanation"]
    assert "Relações removidas" in data["explanation"]


def test_cli_includes_meta_summary(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--include-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    meta = data.get("meta_summary")
    assert meta is not None
    assert meta["route"] == "text"
    assert meta["input_size"] >= 1
    assert meta["answer"]
