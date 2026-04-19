import pytest

import hunt


def test_classify_target_recognizes_ipv4():
    assert hunt.classify_target("1.2.3.4") == {"kind": "ip", "target": "1.2.3.4"}


def test_classify_target_recognizes_cidr():
    assert hunt.classify_target("1.2.3.0/24") == {"kind": "cidr", "target": "1.2.3.0/24"}


def test_classify_target_treats_domain_as_domain():
    assert hunt.classify_target("example.com") == {"kind": "domain", "target": "example.com"}


def test_classify_target_rejects_invalid_ip_like_values():
    with pytest.raises(ValueError, match="invalid IP/CIDR target"):
        hunt.classify_target("999.1.2.3")


def test_run_recon_passes_ip_target_to_subprocess(monkeypatch):
    captured = {}

    class FakeProc:
        returncode = 0

        def wait(self, timeout=None):
            captured["timeout"] = timeout
            return 0

    def fake_popen(cmd, shell, cwd, **kwargs):
        captured["cmd"] = cmd
        captured["shell"] = shell
        captured["cwd"] = cwd
        captured["start_new_session"] = kwargs.get("start_new_session")
        return FakeProc()

    monkeypatch.setattr(hunt.subprocess, "Popen", fake_popen)

    assert hunt.run_recon("1.2.3.4") is True
    assert '"1.2.3.4"' in captured["cmd"]
    assert captured["shell"] is True
    assert captured["cwd"] == hunt.BASE_DIR
    assert captured["start_new_session"] is True
    assert captured["timeout"] == 1800


def test_run_recon_kills_process_group_when_wait_times_out(monkeypatch):
    captured = []

    class FakeProc:
        pid = 5150
        returncode = None

        def wait(self, timeout=None):
            raise hunt.subprocess.TimeoutExpired(cmd="recon", timeout=timeout)

    monkeypatch.setattr(hunt.subprocess, "Popen", lambda *args, **kwargs: FakeProc())
    monkeypatch.setattr(hunt.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(hunt.os, "killpg", lambda pid, sig: captured.append((pid, sig)))

    assert hunt.run_recon("example.com") is False
    assert captured


def test_hunt_target_uses_canonical_cidr_across_followup_paths(monkeypatch):
    seen = {
        "recon": [],
        "scan": [],
        "profile": [],
        "summary": [],
        "reports": [],
    }

    monkeypatch.setattr(hunt, "run_recon", lambda target, quick=False: seen["recon"].append(target) or True)
    monkeypatch.setattr(hunt, "run_vuln_scan", lambda target, quick=False: seen["scan"].append(target) or True)
    monkeypatch.setattr(
        hunt,
        "_update_target_profile",
        lambda target, *, elapsed_minutes=0, recon_completed=False: seen["profile"].append(target),
    )
    monkeypatch.setattr(
        hunt,
        "_auto_log_session_summary",
        lambda target, **kwargs: seen["summary"].append(target),
    )
    monkeypatch.setattr(hunt, "generate_reports", lambda target: seen["reports"].append(target) or 0)

    result = hunt.hunt_target("1.2.3.4/24")

    assert result["domain"] == "1.2.3.0/24"
    assert seen == {
        "recon": ["1.2.3.0/24"],
        "scan": ["1.2.3.0/24"],
        "profile": ["1.2.3.0/24"],
        "summary": ["1.2.3.0/24"],
        "reports": ["1.2.3.0/24"],
    }


def test_run_vuln_scan_uses_cidr_storage_dir(monkeypatch, tmp_path):
    recon_root = tmp_path / "recon"
    findings_root = tmp_path / "findings"
    reports_root = tmp_path / "reports"
    stored_recon_dir = recon_root / "1.2.3.0_24"
    stored_recon_dir.mkdir(parents=True)

    monkeypatch.setattr(hunt, "RECON_DIR", str(recon_root))
    monkeypatch.setattr(hunt, "FINDINGS_DIR", str(findings_root))
    monkeypatch.setattr(hunt, "REPORTS_DIR", str(reports_root))

    captured = {}

    class FakeProc:
        returncode = 0

        def wait(self, timeout=None):
            captured["timeout"] = timeout
            return 0

    def fake_popen(cmd, shell, cwd, **kwargs):
        captured["cmd"] = cmd
        captured["shell"] = shell
        captured["cwd"] = cwd
        captured["start_new_session"] = kwargs.get("start_new_session")
        return FakeProc()

    monkeypatch.setattr(hunt.subprocess, "Popen", fake_popen)

    assert hunt.run_vuln_scan("1.2.3.0/24") is True
    assert str(stored_recon_dir) in captured["cmd"]
    assert "1.2.3.0/24" not in captured["cmd"]
    assert captured["cwd"] == hunt.BASE_DIR
    assert captured["start_new_session"] is True
    assert captured["timeout"] == 1800


def test_run_vuln_scan_kills_process_group_when_wait_times_out(monkeypatch, tmp_path):
    recon_root = tmp_path / "recon"
    stored_recon_dir = recon_root / "example.com"
    stored_recon_dir.mkdir(parents=True)
    monkeypatch.setattr(hunt, "RECON_DIR", str(recon_root))

    captured = []

    class FakeProc:
        pid = 6160
        returncode = None

        def wait(self, timeout=None):
            raise hunt.subprocess.TimeoutExpired(cmd="scan", timeout=timeout)

    monkeypatch.setattr(hunt.subprocess, "Popen", lambda *args, **kwargs: FakeProc())
    monkeypatch.setattr(hunt.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(hunt.os, "killpg", lambda pid, sig: captured.append((pid, sig)))

    assert hunt.run_vuln_scan("example.com") is False
    assert captured


def test_generate_reports_uses_cidr_storage_dirs(monkeypatch, tmp_path):
    findings_root = tmp_path / "findings"
    reports_root = tmp_path / "reports"
    stored_findings_dir = findings_root / "1.2.3.0_24"
    stored_report_dir = reports_root / "1.2.3.0_24"
    stored_findings_dir.mkdir(parents=True)
    stored_report_dir.mkdir(parents=True)
    (stored_report_dir / "test.md").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(hunt, "FINDINGS_DIR", str(findings_root))
    monkeypatch.setattr(hunt, "REPORTS_DIR", str(reports_root))

    captured = {}

    def fake_run_cmd(cmd, cwd=None, timeout=600):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return True, "generated"

    monkeypatch.setattr(hunt, "run_cmd", fake_run_cmd)

    assert hunt.generate_reports("1.2.3.0/24") == 1
    assert str(stored_findings_dir) in captured["cmd"]
    assert "1.2.3.0/24" not in captured["cmd"]
