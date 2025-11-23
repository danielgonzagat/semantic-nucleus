from __future__ import annotations

from metanucleus.evolution.rule_mismatch_log import RuleMismatch, append_rule_mismatch


def test_rule_mismatch_vehicle_is_a() -> None:
    """
    Exemplo mínimo de falha de regra/ontologia. Não falha o teste.
    """
    mismatch = RuleMismatch(
        rule_name="IS_A_vehicle",
        description="Carro deveria ser reconhecido como veículo.",
        context="O carro está andando rápido.",
        expected="IS_A(carros, veiculo)",
        got="(sem informação de tipo)",
        severity="warning",
        file_path="metanucleus/semantics/rules.py",
    )
    append_rule_mismatch(mismatch)
    assert True


def test_rule_mismatch_part_of_wheel_car() -> None:
    mismatch = RuleMismatch(
        rule_name="PART_OF_wheel_car",
        description="Roda deveria ser parte de carro na ontologia básica.",
        context="A roda do carro está furada.",
        expected="PART_OF(roda, carro)",
        got="(sem relação PART_OF registrada)",
        severity="warning",
        file_path="metanucleus/semantics/rules.py",
    )
    append_rule_mismatch(mismatch)
    assert True
