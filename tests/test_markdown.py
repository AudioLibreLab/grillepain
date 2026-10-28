import difflib
from pathlib import Path

import pytest

from grillepain.report.markdown import render
from helpers import run_result

REF = Path(__file__).resolve().parent.parent / "examples" / "MySong_20261027_183119_analyse.md"


def test_warning_line(sample_result_faible):
    assert "**Attention :** Calage du temps 1 peu fiable" in render(sample_result_faible)


def test_no_warning_when_reliable(sample_result):
    assert "**Attention :**" not in render(sample_result)


@pytest.mark.golden
def test_identical_to_reference(example_mkv):
    md = render(run_result(example_mkv))
    ref = REF.read_text(encoding="utf-8")

    def strip(s: str) -> str:
        return "\n".join(l for l in s.splitlines() if not l.startswith("**Attention :**"))

    a, b = strip(ref), strip(md)
    diff = "\n".join(difflib.unified_diff(a.splitlines(), b.splitlines(), "référence", "package", lineterm=""))
    assert a == b, diff
