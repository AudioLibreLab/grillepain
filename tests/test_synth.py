import librosa
import numpy as np
import synth


def test_pluck_pitch():
    y = synth.pluck(60, 1.0)
    f0, *_ = librosa.pyin(y, fmin=75, fmax=1400, sr=22050)
    assert abs(np.nanmedian(69 + 12 * np.log2(f0 / 440)) - 60) < 0.3


def test_backing_length_and_count_in():
    y = synth.chord_backing("C7|F7", bpm=120, beats_per_bar=4, start_s=2.5, choruses=2, count_in=True)
    assert len(y) >= int((2.5 + 16 * 0.5) * 22050)
    on = librosa.onset.onset_detect(y=y, sr=22050, units="time")
    assert abs(on[0] - 0.5) < 0.03 and abs(on[3] - 2.0) < 0.03  # clics à 0.5, 1.0, 1.5, 2.0


def test_make_mkv(tmp_path):
    p = tmp_path / "x.mkv"
    synth.make_mkv(p, synth.silence(1), synth.silence(1))
    assert p.exists() and p.stat().st_size > 0
