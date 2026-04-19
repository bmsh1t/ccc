# Upstream `97d4efb` Migration Alignment — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small compatibility bridge so the local repo can keep its current hunt/report/memory workflow while reducing direct coupling to legacy modules that upstream `97d4efb` later deletes.

**Architecture:** Introduce one focused bridge module that owns three legacy capability entrypoints: journal creation, CVE-hunt dispatch, and report generation dispatch. Then migrate `tools/hunt.py`, `agent.py`, and the direct `HuntJournal(...)` call sites onto that bridge without changing user-visible command names or tool behavior. Keep the existing legacy files in place for now; this phase is about narrowing dependency edges, not deleting implementations.

**Tech Stack:** Python 3, pytest, existing `tools/` scripts, hunt memory JSONL backend, subprocess-based wrappers

---

## File structure

- `tools/legacy_bridge.py` — new compatibility bridge for journal access, CVE hunter dispatch, and report generator dispatch
- `tests/test_legacy_bridge.py` — focused regression tests for the new bridge contract
- `tools/hunt.py` — swap direct legacy module assumptions to bridge calls while keeping current CLI behavior
- `agent.py` — route `run_cve_hunt`, `generate_reports`, and session summary journaling through the bridge
- `tools/remember.py` — use the bridge for journal creation instead of importing `HuntJournal` directly
- `tools/resume.py` — same journal bridge migration
- `memory/__init__.py` — re-export `HuntJournal` from the bridge-backed path so package consumers depend on one stable memory entrypoint
- `tests/test_hunt_wrappers.py` — extend wrapper coverage for bridge-based CVE/report paths
- `tests/test_agent_dispatcher_misc.py` — confirm agent dispatch still surfaces report counts through unchanged tool names
- `tests/test_hunt_journal.py` / `tests/test_resume_tool.py` / `tests/test_remember_tool.py` / `tests/test_autopilot_state_tool.py` / `tests/test_autopilot_mode.py` — existing memory regressions that prove journal behavior stays stable

### Task 1: Add the legacy compatibility bridge with failing tests first

**Files:**
- Create: `tools/legacy_bridge.py`
- Create: `tests/test_legacy_bridge.py`

- [ ] **Step 1: Write the failing bridge tests**

Create `tests/test_legacy_bridge.py` with these tests:

```python
"""Regression tests for tools/legacy_bridge.py."""

from __future__ import annotations

from pathlib import Path

import legacy_bridge


def test_open_hunt_journal_uses_expected_jsonl_path(tmp_path):
    journal = legacy_bridge.open_hunt_journal(tmp_path)

    assert journal.path == Path(tmp_path) / "journal.jsonl"


def test_run_legacy_cve_hunt_executes_cve_hunter_script(monkeypatch, tmp_path):
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
    assert 'cve_hunter.py' in captured["cmd"]
    assert '--recon-dir "' in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 77


def test_generate_legacy_reports_executes_report_generator(monkeypatch, tmp_path):
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
    assert 'report_generator.py' in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 45
```

- [ ] **Step 2: Run the new tests to verify red**

Run: `pytest -q tests/test_legacy_bridge.py`

Expected: FAIL because `tools/legacy_bridge.py` does not exist yet.

- [ ] **Step 3: Implement the minimal bridge**

Create `tools/legacy_bridge.py` with this structure:

```python
"""Compatibility bridge for legacy hunt/report/memory capabilities."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from memory.hunt_journal import HuntJournal
from runtime_exec import run_shell_command


def open_hunt_journal(memory_dir: str | Path) -> HuntJournal:
    return HuntJournal(Path(memory_dir) / "journal.jsonl")


def run_legacy_cve_hunt(
    domain: str,
    *,
    base_dir: str,
    recon_dir: str | None = None,
    timeout: int = 600,
) -> tuple[bool, str]:
    script = os.path.join(base_dir, "tools", "cve_hunter.py")
    recon_flag = f' --recon-dir "{recon_dir}"' if recon_dir else ""
    cmd = f'python3 "{script}" "{domain}"{recon_flag}'
    return run_shell_command(cmd, cwd=base_dir, timeout=timeout)


def generate_legacy_reports(
    findings_dir: str,
    *,
    base_dir: str,
    timeout: int = 600,
) -> tuple[bool, str]:
    script = os.path.join(base_dir, "tools", "report_generator.py")
    cmd = f'python3 "{script}" "{findings_dir}"'
    return run_shell_command(cmd, cwd=base_dir, timeout=timeout)
```

- [ ] **Step 4: Run the bridge tests to verify green**

Run: `pytest -q tests/test_legacy_bridge.py`

Expected: PASS.

- [ ] **Step 5: Commit the bridge layer**

```bash
git add tools/legacy_bridge.py tests/test_legacy_bridge.py
git commit -m "feat: add legacy capability bridge"
```

### Task 2: Move `tools/hunt.py` onto the bridge without changing CLI behavior

**Files:**
- Modify: `tools/hunt.py`
- Modify: `tests/test_hunt_wrappers.py`
- Modify: `tests/test_hunt_target_types.py`

- [ ] **Step 1: Write the failing wrapper regressions first**

Append these tests to `tests/test_hunt_wrappers.py`:

```python
def test_run_cve_hunt_uses_legacy_bridge(monkeypatch, tmp_path):
    domain = "example.com"
    recon_root = tmp_path / "recon"
    (recon_root / domain).mkdir(parents=True)
    monkeypatch.setattr(hunt, "RECON_DIR", str(recon_root))

    captured = {}

    def fake_run_legacy_cve_hunt(target, *, base_dir, recon_dir=None, timeout=600):
        captured["target"] = target
        captured["base_dir"] = base_dir
        captured["recon_dir"] = recon_dir
        captured["timeout"] = timeout
        return True, "ok"

    monkeypatch.setattr(hunt, "run_legacy_cve_hunt", fake_run_legacy_cve_hunt, raising=False)

    assert hunt.run_cve_hunt(domain) is True
    assert captured["target"] == domain
    assert captured["base_dir"] == hunt.BASE_DIR
    assert captured["recon_dir"] == hunt._resolve_recon_dir(domain)
    assert captured["timeout"] == 600


def test_generate_reports_uses_legacy_bridge(monkeypatch, tmp_path):
    domain = "example.com"
    findings_root = tmp_path / "findings"
    reports_root = tmp_path / "reports"
    (findings_root / domain).mkdir(parents=True)
    (reports_root / domain).mkdir(parents=True)
    (reports_root / domain / "report-a.md").write_text("ok", encoding="utf-8")
    monkeypatch.setattr(hunt, "FINDINGS_DIR", str(findings_root))
    monkeypatch.setattr(hunt, "REPORTS_DIR", str(reports_root))

    captured = {}

    def fake_generate_legacy_reports(findings_dir, *, base_dir, timeout=600):
        captured["findings_dir"] = findings_dir
        captured["base_dir"] = base_dir
        captured["timeout"] = timeout
        return True, "generated"

    monkeypatch.setattr(hunt, "generate_legacy_reports", fake_generate_legacy_reports, raising=False)

    assert hunt.generate_reports(domain) == 1
    assert captured["findings_dir"] == hunt._resolve_findings_dir(domain)
    assert captured["base_dir"] == hunt.BASE_DIR
    assert captured["timeout"] == 600
```

- [ ] **Step 2: Run the wrapper tests to verify red**

Run: `pytest -q tests/test_hunt_wrappers.py -k "legacy_bridge"`

Expected: FAIL because `tools/hunt.py` still shells the legacy scripts directly.

- [ ] **Step 3: Switch `tools/hunt.py` to the bridge**

Near the existing imports in `tools/hunt.py`, add:

```python
from legacy_bridge import generate_legacy_reports, open_hunt_journal, run_legacy_cve_hunt
```

Replace the direct `HuntJournal(...)` construction sites with:

```python
journal = open_hunt_journal(HUNT_MEMORY_DIR)
```

Update `generate_reports()` to:

```python
def generate_reports(domain):
    """Generate reports for findings."""
    findings_dir = _resolve_findings_dir(domain)
    if not os.path.isdir(findings_dir):
        log("warn", f"No findings for {domain}")
        return 0

    log("info", f"Generating reports for {domain}...")
    success, output = generate_legacy_reports(findings_dir, base_dir=BASE_DIR, timeout=600)
    print(output)

    report_dir = _resolve_reports_dir(domain)
    if os.path.isdir(report_dir):
        return len([f for f in os.listdir(report_dir) if f.endswith(".md") and f != "SUMMARY.md"])
    return 0
```

Update `run_cve_hunt()` to:

```python
def run_cve_hunt(domain):
    """Run CVE hunter on a target."""
    log("info", f"Running CVE hunter on {domain}...")
    recon_dir = _resolve_recon_dir(domain)
    if not os.path.isdir(recon_dir):
        recon_dir = None

    success, output = run_legacy_cve_hunt(
        domain,
        base_dir=BASE_DIR,
        recon_dir=recon_dir,
        timeout=600,
    )
    if output:
        print(output)
    return success
```

Do not change the public function names, arguments, or return shapes.

- [ ] **Step 4: Run the focused hunt regressions**

Run:
- `pytest -q tests/test_hunt_wrappers.py`
- `pytest -q tests/test_hunt_target_types.py`

Expected: PASS.

- [ ] **Step 5: Commit the hunt migration**

```bash
git add tools/hunt.py tests/test_hunt_wrappers.py tests/test_hunt_target_types.py
git commit -m "refactor: route hunt legacy actions through bridge"
```

### Task 3: Move `agent.py`, `remember.py`, and `resume.py` to bridge-backed journal/report/CVE entrypoints

**Files:**
- Modify: `agent.py`
- Modify: `tools/remember.py`
- Modify: `tools/resume.py`
- Modify: `memory/__init__.py`
- Modify: `tests/test_agent_dispatcher_misc.py`

- [ ] **Step 1: Write the failing agent and journal import tests**

Append this test to `tests/test_agent_dispatcher_misc.py`:

```python
def test_dispatch_generate_reports_uses_bridge_backed_hunt(monkeypatch, tmp_path):
    from agent import ToolDispatcher

    class FakeHunt:
        BASE_DIR = str(tmp_path)

        @staticmethod
        def generate_reports(domain):
            assert domain == "example.com"
            return 2

    dispatcher = ToolDispatcher(FakeHunt(), "example.com")
    output = dispatcher.dispatch("generate_reports", {})

    assert "generate_reports: 2 report(s) generated" in output
```

Append these tests to `tests/test_legacy_bridge.py`:

```python
def test_memory_package_reexports_hunt_journal():
    from memory import HuntJournal

    assert HuntJournal.__name__ == "HuntJournal"
```

- [ ] **Step 2: Run the focused tests to verify current red/coverage gap**

Run:
- `pytest -q tests/test_agent_dispatcher_misc.py -k "bridge_backed_hunt"`
- `pytest -q tests/test_legacy_bridge.py`

Expected: the new agent test should fail until the bridge-backed imports are wired, while the bridge test suite remains otherwise green.

- [ ] **Step 3: Migrate the journal call sites and agent entrypoints**

In `agent.py`, replace:

```python
from memory.hunt_journal import HuntJournal
```

with:

```python
from memory import HuntJournal
from tools.legacy_bridge import open_hunt_journal
```

Then replace the session-summary construction site with:

```python
journal = open_hunt_journal(memory_dir)
```

In `tools/remember.py`, replace:

```python
from memory.hunt_journal import HuntJournal
```

with:

```python
from legacy_bridge import open_hunt_journal
```

and replace:

```python
journal = HuntJournal(memory_dir / "journal.jsonl")
```

with:

```python
journal = open_hunt_journal(memory_dir)
```

Do the same shape in `tools/resume.py`.

In `memory/__init__.py`, replace:

```python
from memory.hunt_journal import HuntJournal
```

with:

```python
from memory.hunt_journal import HuntJournal
```

but add an explicit comment above it:

```python
# Compatibility re-export kept stable while upstream migration is in progress.
```

This task is intentionally conservative: `memory.__init__` keeps the same symbol, but the higher-level callers stop reaching into `memory.hunt_journal` directly.

- [ ] **Step 4: Run the focused memory + agent regressions**

Run:
- `pytest -q tests/test_agent_dispatcher_misc.py`
- `pytest -q tests/test_remember_tool.py tests/test_resume_tool.py`
- `pytest -q tests/test_hunt_journal.py tests/test_autopilot_state_tool.py tests/test_autopilot_mode.py`

Expected: PASS.

- [ ] **Step 5: Commit the caller migration**

```bash
git add agent.py tools/remember.py tools/resume.py memory/__init__.py tests/test_agent_dispatcher_misc.py tests/test_legacy_bridge.py
git commit -m "refactor: narrow legacy journal entrypoints"
```

### Task 4: Final verification and handoff

**Files:**
- Verify only

- [ ] **Step 1: Run the focused migration suite**

Run:

```bash
pytest -q tests/test_legacy_bridge.py tests/test_hunt_wrappers.py tests/test_hunt_target_types.py tests/test_agent_dispatcher_misc.py tests/test_remember_tool.py tests/test_resume_tool.py tests/test_hunt_journal.py tests/test_autopilot_state_tool.py tests/test_autopilot_mode.py
```

Expected: PASS.

- [ ] **Step 2: Run the full regression suite**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 3: Audit the final diff is scoped correctly**

Run:

```bash
git diff --stat main..HEAD
```

Expected touched files are limited to:
- `docs/superpowers/plans/2026-04-20-upstream-97d4efb-migration-phase1.md`
- `tools/legacy_bridge.py`
- `tests/test_legacy_bridge.py`
- `tools/hunt.py`
- `agent.py`
- `tools/remember.py`
- `tools/resume.py`
- `memory/__init__.py`
- `tests/test_hunt_wrappers.py`
- `tests/test_hunt_target_types.py`
- `tests/test_agent_dispatcher_misc.py`

- [ ] **Step 4: Commit any final verification-only adjustment if needed**

```bash
git add -A
git commit -m "test: cover 97d4efb migration phase1"
```

Only do this if verification uncovered a small last-mile test fix. Otherwise skip this commit.
