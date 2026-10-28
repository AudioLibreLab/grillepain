import json
from pathlib import Path

import pytest

from grillepain.errors import DetectionError
from grillepain.form import place_notes
from grillepain.metrics import compute
from grillepain.notes import Note

from helpers import run_pipeline

REF = Path(__file__).resolve().parent.parent / "examples" / "MySong_20261027_183119_prototype.json"


def test_penta_only_solo(al, bc, bars):  # C Eb F G Bb, une note par temps, mesures 1-4
    notes = [Note(1.0 + 0.5 * i, 0.4, [60, 63, 65, 67, 70][i % 5], -10) for i in range(16)]
    m = compute(place_notes(notes, al, bc, 4), al, bc, bars, 4)
    assert m["minor_penta_pct"] == 100.0 and m["key"] == "C"
    assert m["per_chord"]["C7"]["third_count"] == 0


def test_arrival_is_first_note_near_downbeat(al, bc, bars):
    notes = [Note(1.0, 0.4, 64, -10), Note(1.5, 0.4, 67, -10)]   # E au temps 1 de la mesure 1
    m = compute(place_notes(notes, al, bc, 4), al, bc, bars, 4)
    assert m["arrivals"][0]["bars"][0] == "E(3)"


def test_empty_raises(al, bc, bars):
    with pytest.raises(DetectionError):
        compute([], al, bc, bars, 4)


@pytest.mark.golden
def test_matches_prototype(example_mkv):
    ref = json.loads(REF.read_text())
    assert run_pipeline(example_mkv) == ref["results"]
