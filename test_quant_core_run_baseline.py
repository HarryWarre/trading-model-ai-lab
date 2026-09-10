import pytest

from quant_core.run_baseline import parse_costs


def test_parse_costs_preserves_preregistered_order():
    assert parse_costs("0,0.0001,0.0002,0.0004") == [0.0, 0.0001, 0.0002, 0.0004]


def test_parse_costs_rejects_negative():
    with pytest.raises(ValueError):
        parse_costs("0,-0.1")
