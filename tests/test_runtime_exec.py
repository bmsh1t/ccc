"""Regression tests for tools/runtime_exec.py."""

from __future__ import annotations

import signal
import subprocess

import runtime_exec


def test_run_shell_command_returns_combined_output(monkeypatch):
    class FakeProc:
        pid = 4242
        returncode = 0

        def communicate(self, timeout=None):
            assert timeout == 30
            return ("ok stdout\n", "warn stderr\n")

    monkeypatch.setattr(runtime_exec.subprocess, "Popen", lambda *_args, **_kwargs: FakeProc())

    success, output = runtime_exec.run_shell_command("echo ok", timeout=30)

    assert success is True
    assert output == "ok stdout\nwarn stderr\n"


def test_run_shell_command_kills_process_group_on_timeout(monkeypatch):
    events = []
    calls = {"communicate": 0}

    class FakeProc:
        pid = 9001
        returncode = None

        def communicate(self, timeout=None):
            calls["communicate"] += 1
            events.append(("communicate", timeout))
            if calls["communicate"] in (1, 2):
                raise subprocess.TimeoutExpired(cmd="boom", timeout=timeout)
            return ("", "")

    monkeypatch.setattr(runtime_exec.subprocess, "Popen", lambda *_a, **_k: FakeProc())
    monkeypatch.setattr(runtime_exec.os, "killpg", lambda pid, sig: events.append(("killpg", pid, sig)))
    monkeypatch.setattr(runtime_exec.os, "getpgid", lambda pid: pid)

    success, output = runtime_exec.run_shell_command("sleep 60", timeout=5)

    assert success is False
    assert "timed out after 5s" in output.lower()
    assert ("killpg", 9001, signal.SIGTERM) in events
    assert ("killpg", 9001, signal.SIGKILL) in events


def test_run_shell_command_split_preserves_stdout_and_stderr(monkeypatch):
    class FakeProc:
        pid = 1337
        returncode = 7

        def communicate(self, timeout=None):
            assert timeout == 10
            return ("out", "err")

    monkeypatch.setattr(runtime_exec.subprocess, "Popen", lambda *_a, **_k: FakeProc())

    success, stdout, stderr = runtime_exec.run_shell_command_split("exit 7", timeout=10)

    assert success is False
    assert stdout == "out"
    assert stderr == "err"
