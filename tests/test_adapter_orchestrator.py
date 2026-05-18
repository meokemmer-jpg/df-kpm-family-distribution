
# K12+K13+K16 Trinity-CONTRARIAN 2026-05-17 (Cross-LLM-validated)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-contrarian-v1") -> dict:
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

def k13_anchor(payload_hash: str) -> dict:
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }

def k16_lock_or_exit(df_name: str):
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)

"""Tests fuer DF-KPM-Family-Distribution Orchestrator [CRUX-MK]."""

from unittest.mock import patch
import pytest

from src.adapter_orchestrator import main


def test_main_mock_default(monkeypatch):
    monkeypatch.delenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", raising=False)
    with patch("src.adapter_orchestrator.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        with patch("src.adapter_orchestrator.log_audit_event"):
            rc = main([])
    assert rc == 0


def test_main_real_without_phronesis(monkeypatch):
    monkeypatch.setenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", "true")
    monkeypatch.delenv("PHRONESIS_TICKET", raising=False)
    with patch("src.adapter_orchestrator.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        with patch("src.adapter_orchestrator.log_audit_event"):
            rc = main([])
    assert rc == 1


def test_main_stop_flag(tmp_path):
    stop_flag = tmp_path / "stop"
    stop_flag.write_text("stop")
    with patch("src.adapter_orchestrator.Path", return_value=stop_flag):
        rc = main([])
    assert rc == 2


def test_main_real_with_phronesis(monkeypatch):
    monkeypatch.setenv("DF_KPM_FAMILY_DIST_REAL_ENABLED", "true")
    monkeypatch.setenv("PHRONESIS_TICKET", "PT-2026-05-11-004")
    with patch("src.adapter_orchestrator.Path") as mock_path:
        mock_path.return_value.exists.return_value = False
        with patch("src.adapter_orchestrator.log_audit_event"):
            rc = main([])
    assert rc == 0
