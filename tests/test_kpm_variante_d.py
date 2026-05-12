"""Tests fuer KPM-Variante-D Helpers (Family-Distribution) [CRUX-MK]."""

from decimal import Decimal
import pytest

from src.kpm_variante_d_helpers import (
    TradingContext,
    DrawdownState,
    kelly_fraction_for_context,
    drawdown_cap_check,
    hive_leverage_gate,
    position_reduction_factor,
)


def test_kelly_fraction_matrix_complete():
    """Alle 5 Trading-Kontexte sind in Matrix."""
    for ctx in TradingContext:
        result = kelly_fraction_for_context(ctx)
        assert isinstance(result, Decimal)
        assert result >= Decimal("0")
        assert result <= Decimal("0.40")


def test_drawdown_cap_negative_raises():
    """Negative Drawdowns sind invalid."""
    with pytest.raises(ValueError):
        drawdown_cap_check(Decimal("-1"))


def test_hive_leverage_gate_full_range():
    """HIVE 0-1 Range testen."""
    assert hive_leverage_gate(Decimal("0.0")) == "auto_deleverage"
    assert hive_leverage_gate(Decimal("0.5")) == "no_leverage_increase"
    assert hive_leverage_gate(Decimal("1.0")) == "leverage_ok"


def test_position_reduction_consistency():
    """Position-Reduction monoton fallend mit Drawdown."""
    n = position_reduction_factor(DrawdownState.NORMAL)
    s = position_reduction_factor(DrawdownState.SOFT_BRAKE)
    h = position_reduction_factor(DrawdownState.HARD_CAP)
    assert n > s > h or n > s >= h
