from pathlib import Path

from real_usmpd_shock_identification_audit import classify, exact_binomial_greater, run


def test_classification_contract():
    assert classify(-0.1) == "conventional"
    assert classify(0.1) == "information"
    assert classify(0.0) == "unclassified"


def test_exact_binomial_known_cases():
    assert exact_binomial_greater(2, 2) == 0.25
    assert exact_binomial_greater(1, 1) == 0.5


def test_full_run(tmp_path):
    result = run(Path("USMPD_2026-09-18.xlsx"),
                 Path("data/usmpd_2026-09-18.manifest.json"), tmp_path)
    assert result["statement_rows"] == 279
    assert result["trading_pnl_computed"] is False
    assert (tmp_path / "research050_manifest.json").is_file()
