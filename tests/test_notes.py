import synth
from grillepain.notes import detect_notes


def test_detects_melody():
    truth = [(0.5, 0.4, 60), (1.0, 0.4, 64), (1.5, 0.4, 67), (2.0, 0.8, 70)]
    notes = detect_notes(synth.melody(truth, 3.0))
    assert [n.midi for n in notes] == [60, 64, 67, 70]
    assert all(abs(n.t_s - t) < 0.02 for n, (t, _, _) in zip(notes, truth))


def test_silence_gives_no_notes():
    assert detect_notes(synth.silence(2.0)) == []
