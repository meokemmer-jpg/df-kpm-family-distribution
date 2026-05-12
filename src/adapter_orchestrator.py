"""DF-KPM-Family-Distribution LaunchAgent-Entry [CRUX-MK]."""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

from .family_distribution_main import (
    create_mock_family,
    compute_family_allocation,
    estimate_wegzugsbesteuerung,
    get_default_mode,
)
from .audit_logger import log_audit_event


def main(argv: list[str] | None = None) -> int:
    stop_flag = Path("/tmp/df-kpm-family-distribution.stop")
    if stop_flag.exists():
        print("STOP.flag detected", file=sys.stderr)
        return 2

    mode = get_default_mode()
    if mode == "real-api" and not os.environ.get("PHRONESIS_TICKET"):
        print("Real-API requires PHRONESIS_TICKET", file=sys.stderr)
        log_audit_event(
            event="real_mode_rejected_no_phronesis",
            df_id="df-kpm-family-distribution",
            details={"reason": "PHRONESIS_TICKET missing"},
        )
        return 1

    # Mock-Default
    family = create_mock_family()
    total_portfolio = Decimal("1000000")
    allocations = compute_family_allocation(total_portfolio, family)

    log_audit_event(
        event="family_allocation_computed",
        df_id="df-kpm-family-distribution",
        details={
            "total_portfolio_eur": str(total_portfolio),
            "member_count": len(family),
            "allocations": [
                {"member_id": a.member_id, "allocated_eur": str(a.allocated_eur)}
                for a in allocations
            ],
            "source": mode,
        },
    )

    # Wegzugsbesteuerung-Pre-Calc (Mock)
    wegzug = estimate_wegzugsbesteuerung(
        unrealized_gains_eur=Decimal("500000"),
    )
    log_audit_event(
        event="wegzugsbesteuerung_estimated",
        df_id="df-kpm-family-distribution",
        details={
            "snapshot_id": wegzug.snapshot_id,
            "estimated_tax_eur": str(wegzug.estimated_tax_eur),
            "tax_rate_pct": str(wegzug.tax_rate_pct),
            "transition_strategy": wegzug.transition_strategy,
        },
    )

    health_data = {
        "status": "ok",
        "timestamp": wegzug.timestamp,
        "family_member_count": len(family),
        "estimated_wegzugs_tax_eur": str(wegzug.estimated_tax_eur),
    }
    health_path = Path("/tmp/df-kpm-family-distribution-health.json")
    try:
        health_path.write_text(json.dumps(health_data, indent=2))
    except Exception as e:
        print(f"Could not write health: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
