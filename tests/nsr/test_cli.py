import json

import pytest

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
    assert meta["phi_plan_description"]
    assert meta["phi_plan_digest"]
    assert meta["phi_plan_program_len"] >= 3
    assert meta["language_category"] == "text"
    assert meta["language_detected"] in {"pt", "en"}
    assert len(meta["meta_digest"]) == 32


def test_cli_meta_summary_includes_lc_calculation(capsys, monkeypatch):
    for target in (
        "maybe_route_math",
        "maybe_route_logic",
        "maybe_route_code",
        "maybe_route_text",
    ):
        monkeypatch.setattr(f"nsr.meta_transformer.{target}", lambda *args, **kwargs: None)
    exit_code = nsr_cli.main(["como você está?", "--format", "json", "--include-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    meta = data.get("meta_summary")
    assert meta is not None
    calc_json = meta.get("meta_calculation")
    assert calc_json
    calc_payload = json.loads(calc_json)
    assert calc_payload["fields"]["operator"]["label"] == "STATE_QUERY"
    assert meta["phi_plan_chain"] == "NORMALIZE→INFER→SUMMARIZE"
    assert meta["phi_plan_ops"] == ["NORMALIZE", "INFER", "SUMMARIZE"]
    assert meta["phi_plan_description"] == "text_phi_state_query"
    assert meta["phi_plan_digest"]
    assert meta["phi_plan_program_len"] == 6
    assert meta["phi_plan_const_len"] == 1
    assert meta["language_category"] == "text"
    assert meta["language_detected"] == "pt"


def test_cli_meta_summary_exposes_plan_metadata_for_math(capsys):
    exit_code = nsr_cli.main(["2+2", "--format", "json", "--include-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    meta = data.get("meta_summary")
    assert meta is not None
    assert meta["phi_plan_description"] == "math_direct_answer"
    assert meta["phi_plan_digest"]
    assert meta["phi_plan_program_len"] == 3
    assert meta["phi_plan_const_len"] == 1
    assert meta["language_category"] in {"text", "unknown"}
    assert "math_ast_operator" in meta
    assert meta["math_ast_language"] in {"pt", "und"}
    assert meta["math_ast_operand_count"] >= 1


def test_cli_meta_summary_exposes_code_ast(capsys):
    code = """
def soma(x, y):
    return x + y
"""
    exit_code = nsr_cli.main([code, "--format", "json", "--include-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    meta = data.get("meta_summary")
    assert meta is not None
    assert meta["code_ast_language"] == "python"
    assert meta["code_ast_node_count"] >= 1


def test_cli_meta_summary_reports_rust_ast(capsys):
    code = """
fn soma(x: i32, y: i32) -> i32 {
    x + y
}
"""
    exit_code = nsr_cli.main([code, "--format", "json", "--include-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    meta = data.get("meta_summary")
    assert meta is not None
    assert meta["code_ast_language"] == "rust"
    assert meta["code_ast_node_count"] >= 1


def test_cli_accepts_expect_meta_digest(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--include-meta"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    digest = payload["meta_summary"]["meta_digest"]
    exit_code = nsr_cli.main(
        ["Um carro existe", "--format", "json", "--include-meta", "--expect-meta-digest", digest]
    )
    assert exit_code == 0


def test_cli_expect_meta_digest_fails_on_mismatch(capsys):
    exit_code = nsr_cli.main(["Um carro existe", "--format", "json", "--include-meta"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    digest = payload["meta_summary"]["meta_digest"]
    bad_digest = digest[:-1] + ("0" if digest[-1] != "0" else "1")
    with pytest.raises(SystemExit):
        nsr_cli.main(
            [
                "Um carro existe",
                "--format",
                "json",
                "--include-meta",
                "--expect-meta-digest",
                bad_digest,
            ]
        )


def test_cli_expect_code_digest(capsys):
    code = """
def soma(x, y):
    return x + y
"""
    exit_code = nsr_cli.main([code, "--format", "json", "--include-meta"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    digest = payload["meta_summary"]["code_summary_digest"]
    assert digest
    exit_code = nsr_cli.main(
        [code, "--format", "json", "--include-meta", "--expect-code-digest", digest]
    )
    assert exit_code == 0


def test_cli_expect_code_digest_fails_on_mismatch(capsys):
    code = """
def soma(x, y):
    return x + y
"""
    exit_code = nsr_cli.main([code, "--format", "json", "--include-meta"])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    digest = payload["meta_summary"]["code_summary_digest"]
    bad_digest = digest[:-1] + ("0" if digest[-1] != "0" else "1")
    with pytest.raises(SystemExit):
        nsr_cli.main(
            [
                code,
                "--format",
                "json",
                "--include-meta",
                "--expect-code-digest",
                bad_digest,
            ]
        )


def test_cli_includes_lc_meta(capsys, monkeypatch):
    for target in (
        "maybe_route_math",
        "maybe_route_logic",
        "maybe_route_code",
        "maybe_route_text",
    ):
        monkeypatch.setattr(f"nsr.meta_transformer.{target}", lambda *args, **kwargs: None)
    exit_code = nsr_cli.main(["como você está?", "--format", "json", "--include-lc-meta"])
    assert exit_code == 0
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(captured)
    lc_meta = data.get("lc_meta")
    assert lc_meta is not None
    lc_meta_obj = json.loads(lc_meta)
    assert lc_meta_obj["kind"] == "STRUCT"
    assert lc_meta_obj["fields"]["tag"]["label"] == "lc_meta"
