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
