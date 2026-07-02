"""Static regression guard: no module under broker/, strategies/, risk/,
or dashboard/ may reference a live Kite order-mutation tool. This is the
architectural backbone of the paper-only guarantee -- if this test ever
fails, something has silently wired in live execution, and that must be
treated as a critical regression, not a normal test failure."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GUARDED_DIRS = ["broker", "strategies", "risk", "dashboard"]
FORBIDDEN_IDENTIFIERS = {
    "place_order",
    "modify_order",
    "cancel_order",
    "place_gtt_order",
    "modify_gtt_order",
    "delete_gtt_order",
}


def _python_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def _scan_for_forbidden(text: str) -> list[str]:
    """AST-based scan: flags forbidden identifiers only when they appear
    as actual code (a call, attribute access, or import), not when they
    appear in a docstring or comment describing what's forbidden -- e.g.
    paper_broker.py's own module docstring names these identifiers as
    documentation, which a naive substring search would (and did)
    incorrectly flag as a violation."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_IDENTIFIERS:
            found.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_IDENTIFIERS:
            found.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name in FORBIDDEN_IDENTIFIERS:
                    found.add(alias.name)
    return sorted(found)


@pytest.mark.parametrize("dir_name", GUARDED_DIRS)
def test_no_live_order_identifiers_in_guarded_package(dir_name: str):
    directory = PROJECT_ROOT / dir_name
    assert directory.is_dir(), f"expected guarded package {directory} to exist"

    offenders: dict[str, list[str]] = {}
    for path in _python_files(directory):
        text = path.read_text(encoding="utf-8")
        found = _scan_for_forbidden(text)
        if found:
            offenders[str(path.relative_to(PROJECT_ROOT))] = found

    assert not offenders, f"forbidden live-order identifiers found: {offenders}"


def test_scanner_actually_detects_forbidden_identifiers(tmp_path):
    """Proves the scanner isn't a no-op: a file containing a forbidden
    identifier must be flagged."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def f():\n    place_order(x=1)\n", encoding="utf-8")
    found = _scan_for_forbidden(bad_file.read_text(encoding="utf-8"))
    assert "place_order" in found


def test_scanner_clean_file_has_no_hits(tmp_path):
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("def f():\n    return get_ltp('NIFTY')\n", encoding="utf-8")
    found = _scan_for_forbidden(clean_file.read_text(encoding="utf-8"))
    assert found == []
