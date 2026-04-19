"""legacy hunt/report/memory 能力的兼容桥接层。"""

from __future__ import annotations

import os
from pathlib import Path

from memory.hunt_journal import HuntJournal
from runtime_exec import run_shell_command


def open_hunt_journal(memory_dir: str | Path) -> HuntJournal:
    """返回 legacy journal 文件对应的 HuntJournal。"""
    return HuntJournal(Path(memory_dir) / "journal.jsonl")


def run_legacy_cve_hunt(
    domain: str,
    *,
    base_dir: str,
    recon_dir: str | None = None,
    timeout: int = 600,
) -> tuple[bool, str]:
    """委托 legacy CVE hunter 脚本执行。"""
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
    """委托 legacy report generator 脚本执行。"""
    script = os.path.join(base_dir, "tools", "report_generator.py")
    cmd = f'python3 "{script}" "{findings_dir}"'
    return run_shell_command(cmd, cwd=base_dir, timeout=timeout)
