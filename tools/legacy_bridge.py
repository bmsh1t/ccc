"""legacy hunt/report/memory 能力的兼容桥接层。"""

from __future__ import annotations

import os
import shlex
from pathlib import Path

from memory.hunt_journal import HuntJournal

try:
    # 兼容 `import tools.legacy_bridge`。
    from .runtime_exec import run_shell_command
except ImportError:
    # 保持 legacy 顶层导入 `import legacy_bridge` 可用。
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
    cmd_parts = ["python3", shlex.quote(script), shlex.quote(domain)]
    if recon_dir:
        cmd_parts.extend(["--recon-dir", shlex.quote(recon_dir)])
    return run_shell_command(" ".join(cmd_parts), cwd=base_dir, timeout=timeout)



def generate_legacy_reports(
    findings_dir: str,
    *,
    base_dir: str,
    timeout: int = 600,
) -> tuple[bool, str]:
    """委托 legacy report generator 脚本执行。"""
    script = os.path.join(base_dir, "tools", "report_generator.py")
    cmd_parts = ["python3", shlex.quote(script), shlex.quote(findings_dir)]
    return run_shell_command(" ".join(cmd_parts), cwd=base_dir, timeout=timeout)
