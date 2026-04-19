"""Regression tests for vuln_scanner.sh stability guards."""

from pathlib import Path


def test_vuln_scanner_bounds_dalfox_and_uses_timeout_helper():
    script = Path(__file__).resolve().parent.parent / "tools" / "vuln_scanner.sh"
    text = script.read_text(encoding="utf-8")

    assert "run_with_timeout()" in text
    assert "timeout_bin()" in text
    assert "dalfox pipe" in text
    assert "--timeout 10" in text
    assert "run_with_timeout" in text
