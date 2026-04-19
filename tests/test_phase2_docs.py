"""Phase 2 文档主工作流提示的回归测试。"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(*relative_paths: str) -> str:
    return "\n".join((REPO_ROOT / path).read_text(encoding="utf-8") for path in relative_paths)


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    [
        ("README.md", "legacy cve/report entrypoints remain available as compatibility paths"),
        ("CLAUDE.md", "legacy cve/report entrypoints remain available as compatibility paths"),
        ("commands/hunt.md", "legacy cve/report entrypoints remain available as compatibility paths"),
    ],
)
def test_primary_workflow_docs_reference_intel_report_and_compatibility_path(
    relative_path: str,
    expected: str,
):
    content = _read(relative_path).lower()

    assert "/intel" in content
    assert "/report" in content
    assert expected in content


def test_intel_doc_marks_legacy_cve_entrypoints_as_compatibility_paths_only():
    content = _read("commands/intel.md").lower()

    assert "primary intel workflow" in content
    assert "compatibility paths only" in content


def test_report_doc_marks_legacy_report_entrypoints_as_compatibility_paths_only():
    content = _read("commands/report.md").lower()

    assert "primary reporting workflow" in content
    assert "compatibility paths only" in content
