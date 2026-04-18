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

    def fake_popen(cmd, shell, cwd):
        captured["cmd"] = cmd
        captured["shell"] = shell
        captured["cwd"] = cwd
        return FakeProc()

    monkeypatch.setattr(hunt.subprocess, "Popen", fake_popen)

    assert hunt.run_recon("1.2.3.4") is True
    assert '"1.2.3.4"' in captured["cmd"]
    assert captured["shell"] is True
    assert captured["cwd"] == hunt.BASE_DIR
    assert captured["timeout"] == 1800
