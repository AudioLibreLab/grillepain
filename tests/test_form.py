import numpy as np

from grillepain.form import place_notes
from grillepain.notes import Note
from grillepain.theory import C_JAM_BLUES, parse_grid
from grillepain.timing import Alignment


def test_placement():
    beats = np.arange(0, 60, 0.5)
    al = Alignment(beats_s=beats, period_s=0.5, bpm=120, downbeat_idx=2, downbeat_s=1.0, method="m", confidence="haute")
    _, bc = parse_grid(C_JAM_BLUES, 4)
    notes = [Note(0.2, 0.2, 60, -10), Note(1.0, 0.3, 64, -10), Note(1.0 + 4 * 2 + 0.25, 0.3, 70, -10),
             Note(1.0 + 48 * 0.5, 0.3, 60, -10)]
    p = place_notes(notes, al, bc, 4)
    assert len(p) == 3                                   # la note d'intro est écartée
    assert (p[0].chorus, p[0].bar, p[0].beat, p[0].chord.sym, p[0].function) == (1, 1, 0.0, "C7", "3")
    assert (p[1].bar, p[1].beat, p[1].chord.sym, p[1].function) == (5, 0.5, "F7", "11")  # Bb sur F7
    assert (p[2].chorus, p[2].bar) == (2, 1)
    assert p[1].to_dict()["chord"] == "F7"
