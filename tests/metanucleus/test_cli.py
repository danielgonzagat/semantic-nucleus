from metanucleus.cli import main


def test_cli_evolve_creates_patch(tmp_path):
    target_file = tmp_path / "sample_module.py"
    target_file.write_text(
        "\n"
        "def redundant(x):\n"
        "    return (x * 2) + (x * 2)\n",
        encoding="utf-8",
    )

    exit_code = main(
        ["evolve", str(target_file), "redundant", "--suite", "none", "--samples", "0,1,2"]
    )

    assert exit_code == 0
    patch_file = target_file.with_suffix(".py.meta.patch")
    assert patch_file.exists()
    assert "return (x * 2) + (x * 2)" in patch_file.read_text(encoding="utf-8")


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
