"""tools/legacy_bridge.py 的回归测试。"""

from __future__ import annotations

from pathlib import Path

import legacy_bridge


def test_open_hunt_journal_returns_journal_jsonl_path(tmp_path):
    journal = legacy_bridge.open_hunt_journal(tmp_path)

    assert journal.path == Path(tmp_path) / "journal.jsonl"


def test_run_legacy_cve_hunt_delegates_to_cve_hunter(monkeypatch, tmp_path):
    captured = {}

    def fake_run_shell_command(cmd, *, cwd=None, timeout=600):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return True, "ok"

    monkeypatch.setattr(legacy_bridge, "run_shell_command", fake_run_shell_command)

    success, output = legacy_bridge.run_legacy_cve_hunt(
        "example.com",
        base_dir=str(tmp_path),
        recon_dir=str(tmp_path / "recon" / "example.com"),
        timeout=77,
    )

    assert success is True
    assert output == "ok"
    assert 'python3 "' in captured["cmd"]
    assert "cve_hunter.py" in captured["cmd"]
    assert '--recon-dir "' in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 77


def test_generate_legacy_reports_delegates_to_report_generator(monkeypatch, tmp_path):
    captured = {}

    def fake_run_shell_command(cmd, *, cwd=None, timeout=600):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return True, "generated"

    monkeypatch.setattr(legacy_bridge, "run_shell_command", fake_run_shell_command)

    success, output = legacy_bridge.generate_legacy_reports(
        str(tmp_path / "findings" / "example.com"),
        base_dir=str(tmp_path),
        timeout=45,
    )

    assert success is True
    assert output == "generated"
    assert "report_generator.py" in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 45
