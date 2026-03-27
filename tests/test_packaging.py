from __future__ import annotations

from pathlib import Path


def test_runtime_dependencies_include_cryptography() -> None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    contents = pyproject.read_text(encoding="utf-8")

    assert '"cryptography>=42.0.0"' in contents


def test_setuptools_package_list_is_explicit() -> None:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    contents = pyproject.read_text(encoding="utf-8")

    assert "[tool.setuptools]" in contents
    assert 'packages = ["scraper"]' in contents
