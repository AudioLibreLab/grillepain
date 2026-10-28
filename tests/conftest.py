import numpy as np
from pathlib import Path

import pytest

from grillepain.theory import C_JAM_BLUES, parse_grid
from grillepain.timing import Alignment

EXAMPLE_MKV = Path(__file__).resolve().parent.parent / "examples" / "MySong_20261027_183119.mkv"


def pytest_configure(config):
    config.addinivalue_line("markers", "golden: test de référence sur l'exemple (ignoré si le .mkv est absent)")


@pytest.fixture
def example_mkv() -> Path:
    if not EXAMPLE_MKV.exists():
        pytest.skip("examples/MySong_20261027_183119.mkv absent")
    return EXAMPLE_MKV


@pytest.fixture
def al() -> Alignment:
    return Alignment(beats_s=np.arange(0, 60, 0.5), period_s=0.5, bpm=120, downbeat_idx=2,
                     downbeat_s=1.0, method="m", method_id="harmonic", confidence="haute")


@pytest.fixture
def bars_bc():
    return parse_grid(C_JAM_BLUES, 4)


@pytest.fixture
def bars(bars_bc):
    return bars_bc[0]


@pytest.fixture
def bc(bars_bc):
    return bars_bc[1]


def _make_result(al: Alignment, bc, bars):
    from grillepain import form, metrics
    from grillepain.notes import Note
    from grillepain.result import Result
    notes = [Note(1.0 + 0.5 * i, 0.4, [60, 63, 65, 67, 70][i % 5], -10.0) for i in range(16)]
    placed = form.place_notes(notes, al, bc, 4)
    m = metrics.compute(placed, al, bc, bars, 4)
    return Result(
        input={"file": "x.mkv", "guitar_track": "guitare", "backing_track": "backing"},
        tune={"name": None, "grid": C_JAM_BLUES, "meter": "4/4", "bars": len(bars)},
        alignment=al, metrics=m, notes=placed, warnings=[])


@pytest.fixture
def sample_result(al, bc, bars):
    return _make_result(al, bc, bars)


@pytest.fixture
def sample_result_faible(al, bc, bars):
    from dataclasses import replace
    return _make_result(replace(al, confidence="faible"), bc, bars)
