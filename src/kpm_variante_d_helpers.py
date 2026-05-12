"""KPM-Variante-D Helpers (Family-Distribution) [CRUX-MK]."""

from __future__ import annotations
from decimal import Decimal
from enum import Enum


class TradingContext(Enum):
    NORMALREGIME_HIGH_CONFIDENCE = "normal_high"
    NORMALREGIME_AVG_CONFIDENCE = "normal_avg"
    HIGH_VOLATILITY = "high_vol"
    WITHDRAWAL_PHASE = "withdrawal"
    REGIME_BREAK = "regime_break"


class DrawdownState(Enum):
    NORMAL = "normal"
    SOFT_BRAKE = "soft_brake"
    HARD_CAP = "hard_cap"
    ABSOLUTE_NO_GO = "absolute_no_go"


KELLY_FRACTION_MATRIX = {
    TradingContext.NORMALREGIME_HIGH_CONFIDENCE: Decimal("0.40"),
    TradingContext.NORMALREGIME_AVG_CONFIDENCE: Decimal("0.30"),
    TradingContext.HIGH_VOLATILITY: Decimal("0.25"),
    TradingContext.WITHDRAWAL_PHASE: Decimal("0.20"),
    TradingContext.REGIME_BREAK: Decimal("0"),
}

DRAWDOWN_SOFT_BRAKE_PCT = Decimal("15")
DRAWDOWN_HARD_CAP_PCT = Decimal("20")
DRAWDOWN_ABSOLUTE_NO_GO_PCT = Decimal("25")
HIVE_LEVERAGE_GATE = Decimal("0.7")
HIVE_AUTO_DELEVERAGE = Decimal("0.5")


def kelly_fraction_for_context(context: TradingContext) -> Decimal:
    if context not in KELLY_FRACTION_MATRIX:
        raise ValueError(f"Unknown context: {context}")
    return KELLY_FRACTION_MATRIX[context]


def drawdown_cap_check(current_drawdown_pct: Decimal) -> DrawdownState:
    if current_drawdown_pct < Decimal("0"):
        raise ValueError(f"Drawdown must be >=0, got {current_drawdown_pct}")
    if current_drawdown_pct >= DRAWDOWN_ABSOLUTE_NO_GO_PCT:
        return DrawdownState.ABSOLUTE_NO_GO
    if current_drawdown_pct >= DRAWDOWN_HARD_CAP_PCT:
        return DrawdownState.HARD_CAP
    if current_drawdown_pct >= DRAWDOWN_SOFT_BRAKE_PCT:
        return DrawdownState.SOFT_BRAKE
    return DrawdownState.NORMAL


def hive_leverage_gate(hive_score: Decimal) -> str:
    if hive_score < Decimal("0") or hive_score > Decimal("1"):
        raise ValueError(f"HIVE-Score must be 0-1, got {hive_score}")
    if hive_score < HIVE_AUTO_DELEVERAGE:
        return "auto_deleverage"
    if hive_score < HIVE_LEVERAGE_GATE:
        return "no_leverage_increase"
    return "leverage_ok"


def position_reduction_factor(state: DrawdownState) -> Decimal:
    if state == DrawdownState.NORMAL:
        return Decimal("1.0")
    if state == DrawdownState.SOFT_BRAKE:
        return Decimal("0.5")
    return Decimal("0.0")
