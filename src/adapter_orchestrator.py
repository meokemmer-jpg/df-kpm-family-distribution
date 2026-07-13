"""DF-KPM-Family-Distribution LaunchAgent-Entry [CRUX-MK]."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

try:  # package import
    from .audit_logger import log_audit_event
    from .family_distribution_main import (
        FamilyMember,
        FamilyRole,
        JurisdictionState,
        compute_family_allocation,
        create_mock_family,
        estimate_wegzugsbesteuerung,
        get_default_mode,
    )
except ImportError:  # direct import from tests via ../src on sys.path
    from audit_logger import log_audit_event
    from family_distribution_main import (
        FamilyMember,
        FamilyRole,
        JurisdictionState,
        compute_family_allocation,
        create_mock_family,
        estimate_wegzugsbesteuerung,
        get_default_mode,
    )


DF_ID = "df-kpm-family-distribution"
DEFAULT_TOTAL_PORTFOLIO_EUR = Decimal("1000000")
DEFAULT_UNREALIZED_GAINS_EUR = Decimal("500000")


def _decimal(value: Any, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{field_name} must be decimal-compatible") from exc


def _member_from_payload(raw: dict[str, Any]) -> FamilyMember:
    return FamilyMember(
        member_id=str(raw["member_id"]),
        name=str(raw.get("name", raw["member_id"])),
        role=FamilyRole(str(raw["role"])),
        jurisdiction=JurisdictionState(str(raw["jurisdiction"])),
        target_share_pct=_decimal(raw["target_share_pct"], "target_share_pct"),
        liquidity_need_eur_year=_decimal(
            raw["liquidity_need_eur_year"],
            "liquidity_need_eur_year",
        ),
        has_cape_coral_coupling=bool(raw.get("has_cape_coral_coupling", False)),
    )


def _load_input(path: Path | None) -> tuple[Decimal, Decimal, Decimal, list[FamilyMember]]:
    if path is None:
        return (
            DEFAULT_TOTAL_PORTFOLIO_EUR,
            DEFAULT_UNREALIZED_GAINS_EUR,
            Decimal("28"),
            create_mock_family(),
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    portfolio = payload.get("portfolio", {})
    members = [_member_from_payload(item) for item in payload["family_members"]]
    return (
        _decimal(portfolio.get("total_eur", DEFAULT_TOTAL_PORTFOLIO_EUR), "total_eur"),
        _decimal(
            portfolio.get("unrealized_gains_eur", DEFAULT_UNREALIZED_GAINS_EUR),
            "unrealized_gains_eur",
        ),
        _decimal(portfolio.get("tax_rate_pct", "28"), "tax_rate_pct"),
        members,
    )


def _risk_decision(
    members: list[FamilyMember],
    total_portfolio_eur: Decimal,
    estimated_tax_eur: Decimal,
) -> dict[str, Any]:
    annual_liquidity_need = sum(
        (member.liquidity_need_eur_year for member in members),
        start=Decimal("0"),
    )
    transition_members = sum(
        1 for member in members if member.jurisdiction == JurisdictionState.TRANSITION
    )
    liquidity_pressure_pct = (
        (annual_liquidity_need + estimated_tax_eur) / total_portfolio_eur
    ) * Decimal("100")

    if transition_members and liquidity_pressure_pct >= Decimal("35"):
        decision = "manual-review"
    elif liquidity_pressure_pct >= Decimal("25"):
        decision = "rebalance-required"
    else:
        decision = "auto-distribute"

    return {
        "decision": decision,
        "annual_liquidity_need_eur": str(annual_liquidity_need),
        "transition_member_count": transition_members,
        "liquidity_pressure_pct": str(liquidity_pressure_pct.quantize(Decimal("0.01"))),
    }


def build_distribution_report(input_path: Path | None, mode: str) -> dict[str, Any]:
    total_portfolio_eur, unrealized_gains_eur, tax_rate_pct, family = _load_input(input_path)
    allocations = compute_family_allocation(total_portfolio_eur, family)
    wegzug = estimate_wegzugsbesteuerung(
        unrealized_gains_eur=unrealized_gains_eur,
        tax_rate_pct=tax_rate_pct,
    )
    risk = _risk_decision(family, total_portfolio_eur, wegzug.estimated_tax_eur)

    return {
        "mission": DF_ID,
        "source": mode,
        "input_path": str(input_path) if input_path else "default",
        "portfolio": {
            "total_eur": str(total_portfolio_eur),
            "unrealized_gains_eur": str(unrealized_gains_eur),
        },
        "family_member_count": len(family),
        "allocations": [
            {
                "member_id": allocation.member_id,
                "allocated_eur": str(allocation.allocated_eur),
                "target_eur": str(allocation.target_eur),
                "drift_eur": str(allocation.drift_eur),
                "liquidity_buffer_eur": str(allocation.liquidity_buffer_eur),
            }
            for allocation in allocations
        ],
        "wegzugsbesteuerung": {
            "snapshot_id": wegzug.snapshot_id,
            "timestamp": wegzug.timestamp,
            "estimated_tax_eur": str(wegzug.estimated_tax_eur),
            "tax_rate_pct": str(wegzug.tax_rate_pct),
            "transition_strategy": wegzug.transition_strategy,
        },
        "risk": risk,
    }


def _write_audit(path: Path | None, event: str, details: dict[str, Any]) -> None:
    if path is None:
        log_audit_event(event=event, df_id=DF_ID, details=details)
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "df_id": DF_ID,
        "details": details,
    }
    serialized = json.dumps(payload, sort_keys=True)
    payload["hmac_sha256"] = hmac.new(
        DF_ID.encode("utf-8"),
        serialized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=DF_ID)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--health-path",
        type=Path,
        default=Path("/tmp/df-kpm-family-distribution-health.json"),
    )
    parser.add_argument("--audit-path", type=Path)
    parser.add_argument(
        "--stop-flag",
        type=Path,
        default=Path("/tmp/df-kpm-family-distribution.stop"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or [])
    if args.stop_flag.exists():
        print("STOP.flag detected", file=sys.stderr)
        return 2

    mode = get_default_mode()
    if mode == "real-api" and not os.environ.get("PHRONESIS_TICKET"):
        print("Real-API requires PHRONESIS_TICKET", file=sys.stderr)
        _write_audit(
            args.audit_path,
            "real_mode_rejected_no_phronesis",
            {"reason": "PHRONESIS_TICKET missing"},
        )
        return 1

    try:
        report = build_distribution_report(args.input, mode)
    except Exception as exc:
        print(f"Could not compute family distribution: {exc}", file=sys.stderr)
        _write_audit(args.audit_path, "family_distribution_rejected", {"reason": str(exc)})
        return 4

    _write_audit(
        args.audit_path,
        "family_allocation_computed",
        {
            "total_portfolio_eur": report["portfolio"]["total_eur"],
            "member_count": report["family_member_count"],
            "risk_decision": report["risk"]["decision"],
            "source": mode,
        },
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    health_data = {
        "status": "ok",
        "timestamp": report["wegzugsbesteuerung"]["timestamp"],
        "family_member_count": report["family_member_count"],
        "estimated_wegzugs_tax_eur": report["wegzugsbesteuerung"]["estimated_tax_eur"],
        "risk_decision": report["risk"]["decision"],
    }
    try:
        args.health_path.parent.mkdir(parents=True, exist_ok=True)
        args.health_path.write_text(
            json.dumps(health_data, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"Could not write health: {exc}", file=sys.stderr)

    return 0


def __df_guarded_entry():  # K16+K11-FOUNDATION-WIRED [CRUX-MK]
    sys.exit(main(sys.argv[1:]))


if __name__ == "__main__":  # K16+K11-FOUNDATION-WIRED [CRUX-MK]
    try:
        from _df_common.df_foundation import run_guarded as _rg
    except Exception:
        raise SystemExit(__df_guarded_entry())
    raise SystemExit(_rg(DF_ID, __df_guarded_entry))
