import pytest

from grillepain.errors import UsageError
from grillepain.theory import C_JAM_BLUES, Chord, parse_grid


def test_functions():
    assert Chord("C7").function(10) == "b7"
    assert Chord("Dm7").function(5) == "b3"
    assert Chord("C7").function(3) == "#9"
    assert Chord("D-7").q == "m7" and Chord("Bbmaj7").root == 10


def test_bad_chords():
    with pytest.raises(UsageError):
        Chord("H7")
    with pytest.raises(UsageError):
        Chord("C7sus4")


def test_two_chords_in_3_4():
    bars, beats = parse_grid("C7 A7|Dm7", 3)
    assert [c.sym for c in beats] == ["C7", "C7", "A7", "Dm7", "Dm7", "Dm7"]


def test_blues_grid():
    bars, beats = parse_grid(C_JAM_BLUES, 4)
    assert len(bars) == 12 and len(beats) == 48 and beats[42].sym == "A7"


@pytest.mark.parametrize("grid,bpb", [("", 4), ("|", 4), ("C7|F7", 0), ("C7|F7", -1)])
def test_bad_grid_or_meter(grid, bpb):
    with pytest.raises(UsageError):
        parse_grid(grid, bpb)


@pytest.mark.parametrize("sym,root", [("Cb7", 11), ("Fbmaj7", 4), ("E#7", 5), ("B#7", 0)])
def test_enharmonic_roots(sym, root):
    assert Chord(sym).root == root
