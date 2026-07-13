"""Functional proof for df-kpm-family-distribution."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adapter_orchestrator import main


def _write_payload(path: Path, target_shares: tuple[str, str, str], transition: bool) -> None:
    jurisdictions = ("transition", "transition", "de") if transition else ("de", "de", "de")
    liquidity_needs = ("220000", "180000", "140000") if transition else ("30000", "25000", "15000")
    payload = {
        "portfolio": {
            "total_eur": "900000",
            "unrealized_gains_eur": "450000",
            "tax_rate_pct": "28",
        },
        "family_members": [
            {
                "member_id": "principal",
                "name": "Principal",
                "role": "principal",
                "jurisdiction": jurisdictions[0],
                "target_share_pct": target_shares[0],
                "liquidity_need_eur_year": liquidity_needs[0],
                "has_cape_coral_coupling": True,
            },
            {
                "member_id": "spouse",
                "name": "Spouse",
                "role": "spouse",
                "jurisdiction": jurisdictions[1],
                "target_share_pct": target_shares[1],
                "liquidity_need_eur_year": liquidity_needs[1],
                "has_cape_coral_coupling": True,
            },
            {
                "member_id": "sibling",
                "name": "Sibling",
                "role": "sibling",
                "jurisdiction": jurisdictions[2],
                "target_share_pct": target_shares[2],
                "liquidity_need_eur_year": liquidity_needs[2],
                "has_cape_coral_coupling": False,
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_case(tmp_path: Path, name: str, target_shares: tuple[str, str, str], transition: bool) -> dict:
    input_path = tmp_path / f"{name}-input.json"
    output_path = tmp_path / f"{name}-output.json"
    health_path = tmp_path / f"{name}-health.json"
    audit_path = tmp_path / f"{name}-audit.jsonl"
    stop_flag = tmp_path / f"{name}.stop"
    _write_payload(input_path, target_shares, transition)

    rc = main(
        [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--health-path",
            str(health_path),
            "--audit-path",
            str(audit_path),
            "--stop-flag",
            str(stop_flag),
        ]
    )

    assert rc == 0
    assert output_path.exists()
    assert health_path.exists()
    assert audit_path.read_text(encoding="utf-8").strip()
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_family_distribution_discriminates_adversarial_transition_input(tmp_path, monkeypatch):
    monkeypatch.delenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", raising=False)
    normal = _run_case(tmp_path, "normal", ("50", "30", "20"), transition=False)
    adversarial = _run_case(tmp_path, "adversarial", ("10", "10", "80"), transition=True)

    normal_allocations = {
        item["member_id"]: Decimal(item["allocated_eur"]) for item in normal["allocations"]
    }
    adversarial_allocations = {
        item["member_id"]: Decimal(item["allocated_eur"]) for item in adversarial["allocations"]
    }

    assert normal["mission"] == adversarial["mission"] == "df-kpm-family-distribution"
    assert normal["portfolio"]["total_eur"] == adversarial["portfolio"]["total_eur"]
    assert normal_allocations["principal"] > adversarial_allocations["principal"]
    assert adversarial_allocations["sibling"] > normal_allocations["sibling"]
    assert normal["risk"]["decision"] == "auto-distribute"
    assert adversarial["risk"]["decision"] == "manual-review"
    assert normal["risk"]["liquidity_pressure_pct"] != adversarial["risk"]["liquidity_pressure_pct"]
