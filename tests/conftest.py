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
                     downbeat_s=1.0, method="m", confidence="haute")


@pytest.fixture
def bars_bc():
    return parse_grid(C_JAM_BLUES, 4)


@pytest.fixture
def bars(bars_bc):
    return bars_bc[0]


@pytest.fixture
def bc(bars_bc):
    return bars_bc[1]
