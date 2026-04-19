"""Regression tests for misc agent dispatcher tool summaries."""

import importlib

import agent
import memory


def _build_dispatcher(tmp_path):
    memory = agent.HuntMemory(str(tmp_path / "agent_session.json"))
    return agent.ToolDispatcher("target.com", memory)


def test_dispatch_check_tools_formats_installed_and_missing(monkeypatch, tmp_path):
    dispatcher = _build_dispatcher(tmp_path)
    hunt = agent._h()
    monkeypatch.setattr(hunt, "check_tools", lambda: (["httpx", "nuclei"], ["sqlmap"]))

    output = dispatcher.dispatch("check_tools", {})

    assert "check_tools: 2 installed, 1 missing" in output
    assert "Installed: httpx, nuclei" in output
    assert "Missing: sqlmap" in output


def test_dispatch_generate_reports_summarizes_output(monkeypatch, tmp_path):
    report_dir = tmp_path / "reports" / "target.com"
    report_dir.mkdir(parents=True)
    (report_dir / "001-test.md").write_text("# report\n", encoding="utf-8")

    dispatcher = _build_dispatcher(tmp_path)
    hunt = agent._h()
    monkeypatch.setattr(hunt, "REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(hunt, "generate_reports", lambda domain: 1)

    output = dispatcher.dispatch("generate_reports", {})

    assert "generate_reports: 1 report(s) generated" in output
    assert "Reports: 001-test.md" in output


def test_dispatch_generate_reports_bridge_backed_hunt_still_summarizes_report_count(
    monkeypatch,
    tmp_path,
):
    domain = "target.com"
    findings_dir = tmp_path / "findings" / domain
    report_dir = tmp_path / "reports" / domain
    findings_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)
    (report_dir / "001-bridge.md").write_text("# report\n", encoding="utf-8")

    dispatcher = _build_dispatcher(tmp_path)
    hunt = agent._h()
    seen = {}

    def fake_generate_legacy_reports(target_findings_dir, *, base_dir, timeout=600):
        seen["findings_dir"] = target_findings_dir
        seen["base_dir"] = base_dir
        seen["timeout"] = timeout
        return True, "generated"

    monkeypatch.setattr(hunt, "FINDINGS_DIR", str(tmp_path / "findings"))
    monkeypatch.setattr(hunt, "REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(hunt._module, "generate_legacy_reports", fake_generate_legacy_reports)

    output = dispatcher.dispatch("generate_reports", {})

    assert seen == {
        "findings_dir": str(findings_dir),
        "base_dir": hunt.BASE_DIR,
        "timeout": 600,
    }
    assert "generate_reports: 1 report(s) generated" in output
    assert "Reports: 001-bridge.md" in output


def test_bridge_backed_hunt_agent_imports_hunt_journal_via_memory_package(monkeypatch):
    sentinel = object()

    with monkeypatch.context() as patch:
        patch.setattr(memory, "HuntJournal", sentinel)
        importlib.reload(agent)
        assert agent.HuntJournal is sentinel

    importlib.reload(agent)
