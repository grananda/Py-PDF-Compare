"""The version is declared once, in pyproject.toml."""
import importlib.metadata
import pathlib
import re

import pdf_compare


def declared_version():
    """The version as written in pyproject.toml, read as text."""
    source = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    match = re.search(r'^version = "([^"]+)"', source.read_text(encoding="utf-8"), re.M)
    assert match, "pyproject.toml declares no version"
    return match.group(1)


def test_package_version_matches_the_distribution():
    """Regression: kept by hand these drifted, and a release shipped saying 2026.2.3."""
    assert pdf_compare.__version__ == importlib.metadata.version("py-pdf-compare")


def test_distribution_version_matches_pyproject():
    """Catches an installed environment left behind by a version bump."""
    assert importlib.metadata.version("py-pdf-compare") == declared_version()
