"""DF-KPM-Family-Distribution Core-Logic [CRUX-MK].

Familien-Verteilungs-Logic: Mitglieder + Liquiditaet + Cape-Coral-Coupling.
Sandbox-Default mit Mock-Familie.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional


class FamilyRole(Enum):
    """Familien-Rolle (fuer Allocation-Logic)."""
    PRINCIPAL = "principal"  # Martin
    SPOUSE = "spouse"        # Gerdi
    SIBLING = "sibling"      # Brueder
    PARENT = "parent"        # Eltern
    CHILD = "child"          # Zukuenftige Kinder


class JurisdictionState(Enum):
    """Aktuelle Jurisdiction (Cape-Coral-Coupling)."""
    DE = "de"  # Deutschland
    US = "us"  # USA Cape-Coral
    TRANSITION = "transition"  # Wegzugsbesteuerung-Phase


@dataclass(frozen=True)
class FamilyMember:
    """Familienmitglied mit Allocation + Liquiditaetsbedarf."""
    member_id: str
    name: str
    role: FamilyRole
    jurisdiction: JurisdictionState
    target_share_pct: Decimal  # 0-100
    liquidity_need_eur_year: Decimal  # Annual cash-need
    has_cape_coral_coupling: bool = False

    def __post_init__(self):
        if self.target_share_pct < Decimal("0") or self.target_share_pct > Decimal("100"):
            raise ValueError(f"target_share_pct must be 0-100, got {self.target_share_pct}")
        if self.liquidity_need_eur_year < Decimal("0"):
            raise ValueError(f"liquidity_need must be >=0, got {self.liquidity_need_eur_year}")


@dataclass(frozen=True)
class AllocationShare:
    """Berechnete Allokation pro Mitglied."""
    member_id: str
    allocated_eur: Decimal
    target_eur: Decimal
    drift_eur: Decimal
    liquidity_buffer_eur: Decimal


@dataclass(frozen=True)
class WegzugsbesteuerungSnapshot:
    """Pre-Calc Wegzugsbesteuerung DE -> USA."""
    snapshot_id: str
    timestamp: str
    total_unrealized_gains_eur: Decimal
    estimated_tax_eur: Decimal
    tax_rate_pct: Decimal  # z.B. 25-45%
    transition_strategy: str  # "stretch" | "lump_sum" | "deferred"
    source: str
    phronesis_ticket: Optional[str] = None

    def __post_init__(self):
        if self.source == "real-api" and not self.phronesis_ticket:
            raise ValueError("Real-API requires phronesis_ticket")


def compute_family_allocation(
    total_portfolio_eur: Decimal,
    members: list[FamilyMember],
) -> list[AllocationShare]:
    """Berechnet Allokation pro Familienmitglied basierend auf target_share_pct."""
    total_share = sum((m.target_share_pct for m in members), start=Decimal("0"))
    if abs(total_share - Decimal("100")) > Decimal("0.5"):
        raise ValueError(f"Family-Member-Shares must sum to ~100, got {total_share}")

    result = []
    for m in members:
        target = total_portfolio_eur * (m.target_share_pct / Decimal("100"))
        # Liquidity-Buffer: 12 Monate Liquiditaetsbedarf
        liquidity_buffer = m.liquidity_need_eur_year
        # Mock: keine Drift in Phase-1 Sandbox
        result.append(AllocationShare(
            member_id=m.member_id,
            allocated_eur=target,
            target_eur=target,
            drift_eur=Decimal("0"),
            liquidity_buffer_eur=liquidity_buffer,
        ))
    return result


def estimate_wegzugsbesteuerung(
    unrealized_gains_eur: Decimal,
    tax_rate_pct: Decimal = Decimal("28"),  # DE Abgeltungssteuer + Soli + KiSt
) -> WegzugsbesteuerungSnapshot:
    """Pre-Calc DE Wegzugsbesteuerung (vereinfachte Phase-1-Naeherung).

    Realistic-Mode in Phase-2: Anwalt-API + AStG §6 + Doppelbesteuerung.
    """
    if unrealized_gains_eur < Decimal("0"):
        raise ValueError("unrealized_gains must be >=0")
    if tax_rate_pct < Decimal("0") or tax_rate_pct > Decimal("100"):
        raise ValueError("tax_rate_pct must be 0-100")

    estimated_tax = unrealized_gains_eur * (tax_rate_pct / Decimal("100"))

    return WegzugsbesteuerungSnapshot(
        snapshot_id=f"wegzug-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        total_unrealized_gains_eur=unrealized_gains_eur,
        estimated_tax_eur=estimated_tax,
        tax_rate_pct=tax_rate_pct,
        transition_strategy="deferred",  # Default: §6 AStG Stundung
        source="mock",
    )


def get_default_mode() -> str:
    """Returns 'mock' (default) or 'real-api'."""
    if os.environ.get("DF_KPM_FAMILY_DIST_REAL_ENABLED") == "true":
        return "real-api"
    return "mock"


def create_mock_family() -> list[FamilyMember]:
    """Mock-Familie fuer Sandbox-Default (Martin + Gerdi + 1 Bruder)."""
    return [
        FamilyMember(
            member_id="martin",
            name="Martin Kemmer",
            role=FamilyRole.PRINCIPAL,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("50"),
            liquidity_need_eur_year=Decimal("120000"),
            has_cape_coral_coupling=True,
        ),
        FamilyMember(
            member_id="gerdi",
            name="Gerdi Kemmer",
            role=FamilyRole.SPOUSE,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("30"),
            liquidity_need_eur_year=Decimal("80000"),
            has_cape_coral_coupling=True,
        ),
        FamilyMember(
            member_id="bruder_1",
            name="Bruder 1 (Mock-Placeholder)",
            role=FamilyRole.SIBLING,
            jurisdiction=JurisdictionState.DE,
            target_share_pct=Decimal("20"),
            liquidity_need_eur_year=Decimal("40000"),
            has_cape_coral_coupling=False,
        ),
    ]
