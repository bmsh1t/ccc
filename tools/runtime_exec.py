"""Shared subprocess execution helpers with process-group cleanup."""

from __future__ import annotations

import os
import signal
import subprocess


def _terminate_process_group(proc: subprocess.Popen[str]) -> None:
    try:
        pgid = os.getpgid(proc.pid)
    except Exception:
        return

    try:
        os.killpg(pgid, signal.SIGTERM)
    except Exception:
        return

    try:
        proc.communicate(timeout=3)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        return

    try:
        os.killpg(pgid, signal.SIGKILL)
    except Exception:
        return

    try:
        proc.communicate(timeout=3)
    except Exception:
        return


def _spawn(cmd: str, *, cwd: str | None = None) -> subprocess.Popen[str]:
    return subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
    )


def run_shell_command(cmd: str, *, cwd: str | None = None, timeout: int = 600) -> tuple[bool, str]:
    proc = _spawn(cmd, cwd=cwd)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_group(proc)
        return False, f"Command timed out after {timeout}s"
    except Exception as exc:
        _terminate_process_group(proc)
        return False, str(exc)
    return proc.returncode == 0, (stdout or "") + (stderr or "")


def run_shell_command_split(
    cmd: str,
    *,
    cwd: str | None = None,
    timeout: int = 600,
) -> tuple[bool, str, str]:
    proc = _spawn(cmd, cwd=cwd)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process_group(proc)
        return False, "", f"Command timed out after {timeout}s"
    except Exception as exc:
        _terminate_process_group(proc)
        return False, "", str(exc)
    return proc.returncode == 0, stdout or "", stderr or ""
