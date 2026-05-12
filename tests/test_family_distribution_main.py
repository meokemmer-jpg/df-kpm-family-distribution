"""Tests fuer DF-KPM-Family-Distribution [CRUX-MK]."""

from __future__ import annotations
from decimal import Decimal
import pytest

from src.family_distribution_main import (
    FamilyMember,
    FamilyRole,
    JurisdictionState,
    AllocationShare,
    WegzugsbesteuerungSnapshot,
    compute_family_allocation,
    estimate_wegzugsbesteuerung,
    get_default_mode,
    create_mock_family,
)


def test_family_member_validation_share():
    """target_share_pct muss 0-100 sein."""
    with pytest.raises(ValueError, match="target_share_pct"):
        FamilyMember(
            member_id="x",
            name="X",
            role=FamilyRole.PRINCIPAL,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("150"),
            liquidity_need_eur_year=Decimal("10000"),
        )


def test_family_member_validation_negative_liquidity():
    """liquidity_need muss >= 0 sein."""
    with pytest.raises(ValueError, match="liquidity_need"):
        FamilyMember(
            member_id="x",
            name="X",
            role=FamilyRole.PRINCIPAL,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("50"),
            liquidity_need_eur_year=Decimal("-1000"),
        )


def test_compute_family_allocation_mock():
    """Mock-Familie -> 50/30/20 Allocation auf 1M Portfolio."""
    family = create_mock_family()
    allocations = compute_family_allocation(Decimal("1000000"), family)
    assert len(allocations) == 3
    # Martin 50%
    assert allocations[0].allocated_eur == Decimal("500000")
    # Gerdi 30%
    assert allocations[1].allocated_eur == Decimal("300000")
    # Bruder 20%
    assert allocations[2].allocated_eur == Decimal("200000")


def test_compute_family_allocation_shares_must_sum_to_100():
    """Family-Shares muessen ~100 summieren."""
    bad_family = [
        FamilyMember(
            member_id="x",
            name="X",
            role=FamilyRole.PRINCIPAL,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("60"),
            liquidity_need_eur_year=Decimal("10000"),
        ),
        FamilyMember(
            member_id="y",
            name="Y",
            role=FamilyRole.SPOUSE,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("30"),  # Sum = 90, not 100
            liquidity_need_eur_year=Decimal("5000"),
        ),
    ]
    with pytest.raises(ValueError, match="100"):
        compute_family_allocation(Decimal("1000000"), bad_family)


def test_estimate_wegzugsbesteuerung_default():
    """500k unrealized * 28% = 140k tax."""
    snap = estimate_wegzugsbesteuerung(Decimal("500000"))
    assert snap.estimated_tax_eur == Decimal("140000.00")
    assert snap.tax_rate_pct == Decimal("28")
    assert snap.transition_strategy == "deferred"
    assert snap.source == "mock"


def test_wegzugsbesteuerung_real_requires_phronesis():
    """Real-API-Source needs phronesis_ticket."""
    with pytest.raises(ValueError, match="phronesis_ticket"):
        WegzugsbesteuerungSnapshot(
            snapshot_id="test",
            timestamp="2026-05-11T10:00:00+00:00",
            total_unrealized_gains_eur=Decimal("100000"),
            estimated_tax_eur=Decimal("28000"),
            tax_rate_pct=Decimal("28"),
            transition_strategy="lump_sum",
            source="real-api",
        )


def test_create_mock_family_3_members():
    """Mock-Family hat 3 Mitglieder mit Cape-Coral-Coupling."""
    family = create_mock_family()
    assert len(family) == 3
    assert family[0].name == "Martin Kemmer"
    assert family[0].has_cape_coral_coupling is True
    assert family[2].role == FamilyRole.SIBLING
    assert family[2].has_cape_coral_coupling is False


def test_get_default_mode_sandbox(monkeypatch):
    monkeypatch.delenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", raising=False)
    assert get_default_mode() == "mock"


def test_get_default_mode_real_strict(monkeypatch):
    monkeypatch.setenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", "yes")
    assert get_default_mode() == "mock"
    monkeypatch.setenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", "true")
    assert get_default_mode() == "real-api"
