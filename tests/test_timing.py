import pytest

import synth
from grillepain.errors import DetectionError, UsageError
from grillepain.theory import C_JAM_BLUES, parse_grid
from grillepain.timing import align


def test_count_in_downbeat():
    y = synth.chord_backing(C_JAM_BLUES, bpm=120, beats_per_bar=4, start_s=2.0, choruses=2, count_in=True)
    _, beats = parse_grid(C_JAM_BLUES, 4)
    a = align(y, beats, bpm_hint=120, downbeat_s=None)
    # accrochage aux temps beat_track, trames de 23 ms
    assert a.method.startswith("décompte") and a.confidence == "haute"
    assert abs(a.downbeat_s - 2.0) < 0.05 and abs(a.bpm - 120) < 1


def test_harmonic_fit_without_count_in():
    y = synth.chord_backing(C_JAM_BLUES, bpm=120, beats_per_bar=4, start_s=1.0, choruses=3, count_in=False)
    _, beats = parse_grid(C_JAM_BLUES, 4)
    a = align(y, beats, bpm_hint=120, downbeat_s=None)
    assert a.method == "ajustement harmonique" and a.method_id == "harmonic"
    # accrochage aux temps beat_track (trames de 23 ms) ; un temps de décalage = 0,5 s
    assert abs(a.downbeat_s - 1.0) < 0.05


def test_manual_downbeat():
    y = synth.chord_backing("C7|F7", bpm=120, beats_per_bar=4, start_s=0.5, choruses=8, count_in=False)
    _, beats = parse_grid("C7|F7", 4)
    a = align(y, beats, bpm_hint=None, downbeat_s=0.5)
    # accrochage aux temps beat_track, trames de 23 ms
    assert a.confidence == "haute" and abs(a.downbeat_s - 0.5) < 0.05


def test_no_pulse():
    with pytest.raises(DetectionError):
        align(synth.silence(3.0), parse_grid("C7", 4)[1], None, None)


def test_downbeat_out_of_range():
    y = synth.chord_backing("C7|F7", bpm=120, beats_per_bar=4, start_s=0.5, choruses=8, count_in=False)
    with pytest.raises(UsageError):
        align(y, parse_grid("C7|F7", 4)[1], None, downbeat_s=999.0)


@pytest.mark.parametrize("bpm", [-10, 0])
def test_bad_bpm(bpm):
    with pytest.raises(UsageError):
        align(synth.silence(3.0), parse_grid("C7", 4)[1], bpm, None)


def test_method_id():
    y = synth.chord_backing(C_JAM_BLUES, bpm=120, beats_per_bar=4, start_s=2.0, choruses=2, count_in=True)
    _, beats = parse_grid(C_JAM_BLUES, 4)
    assert align(y, beats, 120, None).method_id == "count_in"
    assert align(y, beats, 120, 2.0).method_id == "downbeat_arg"
