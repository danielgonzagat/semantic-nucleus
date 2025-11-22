import json

from metanucleus.cli import main


def test_cli_evolve_creates_patch(tmp_path):
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    report_file = tmp_path / "report.json"
    exit_code = main(
        [
            "evolve",
            str(target_file),
            "redundant",
            "--suite",
            "none",
            "--samples",
            "0,1,2",
            "--report",
            str(report_file),
        ]
    )

    assert exit_code == 0
    patch_file = target_file.with_suffix(".py.meta.patch")
    assert patch_file.exists()
    assert "return (x * 2) + (x * 2)" in patch_file.read_text(encoding="utf-8")
    report_data = json.loads(report_file.read_text(encoding="utf-8"))
    assert report_data["target"].endswith("sample_module.py")
    assert report_data["tests"][0]["status"] == "skipped"


def test_cli_evolve_invalid_suite(tmp_path, capsys):
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    exit_code = main(["evolve", str(target_file), "redundant", "--suite", "unknown"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "Suite 'unknown' desconhecida" in captured.out


def test_cli_testcore_command(capsys):
    exit_code = main(["testcore", "basic"])
    captured = capsys.readouterr()
    assert exit_code in (0, 2)  # depende do resultado do suite básico
    assert "[TESTCORE:basic]" in captured.out


def test_cli_evolve_custom_suite(tmp_path):
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )
    suite_file = tmp_path / "suite.json"
    suite_file.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "name": "saudacao",
                        "input": "Oi Metanúcleo!",
                        "expected": {"intent": "greeting", "lang": "pt"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    exit_code = main(
        [
            "evolve",
            str(target_file),
            "redundant",
            "--suite-file",
            str(suite_file),
            "--suite",
            "none",
        ]
    )
    assert exit_code == 0
    assert target_file.with_suffix(".py.meta.patch").exists()


def test_cli_testcore_suite_file(tmp_path, capsys):
    suite_file = tmp_path / "suite.json"
    suite_file.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "name": "saudacao",
                        "input": "Oi Metanúcleo!",
                        "expected": {"intent": "greeting", "lang": "pt"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    exit_code = main(["testcore", "basic", "--suite-file", str(suite_file)])
    captured = capsys.readouterr()
    assert exit_code in (0, 2)
    assert suite_file.name in captured.out
