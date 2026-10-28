from pathlib import Path

import pytest

EXAMPLE_MKV = Path(__file__).resolve().parent.parent / "examples" / "MySong_20261027_183119.mkv"


def pytest_configure(config):
    config.addinivalue_line("markers", "golden: test de référence sur l'exemple (ignoré si le .mkv est absent)")


@pytest.fixture
def example_mkv() -> Path:
    if not EXAMPLE_MKV.exists():
        pytest.skip("examples/MySong_20261027_183119.mkv absent")
    return EXAMPLE_MKV
