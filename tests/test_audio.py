import subprocess

import numpy as np
import pytest
import synth

from grillepain.audio import SR, load_mkv, load_pair
from grillepain.errors import InputError


def test_titles_heuristic(tmp_path):
    g = synth.pluck(60, 1.0)
    b = synth.silence(1.0)
    p = tmp_path / "ma prise é.mkv"
    synth.make_mkv(p, guitar=b, backing=g, titles=("chrome", "carla"))  # ordre inversé
    t = load_mkv(p)
    assert t.guitar_name == "carla" and t.backing_name == "chrome"
    assert np.abs(t.guitar).max() > 0.1
    assert t.source == "autre"


def test_source_ireal(tmp_path):
    p = tmp_path / "a.mkv"
    synth.make_mkv(p, guitar=synth.pluck(60, 1.0), backing=synth.silence(1.0),
                   titles=("carla", "iReal Pro"))
    assert load_mkv(p).source == "ireal"


def test_load_pair(tmp_path):
    g, b = tmp_path / "g.wav", tmp_path / "b.wav"
    synth.write_wav(g, synth.pluck(60, 1.0))
    synth.write_wav(b, synth.silence(1.0))
    t = load_pair(g, b)
    assert t.guitar_name == "g.wav" and t.source == "autre"
    assert abs(len(t.guitar) - SR) < 5


def test_missing_file(tmp_path):
    with pytest.raises(InputError):
        load_mkv(tmp_path / "absent.mkv")
    with pytest.raises(InputError):
        load_pair(tmp_path / "x.wav", tmp_path / "y.wav")


def test_single_track(tmp_path):
    p = tmp_path / "mono.mkv"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=d=1",
                    "-c:a", "flac", str(p)], check=True)
    with pytest.raises(InputError, match="2 pistes"):
        load_mkv(p)


def test_bad_index(tmp_path):
    p = tmp_path / "a.mkv"
    synth.make_mkv(p, guitar=synth.pluck(60, 1.0), backing=synth.silence(1.0))
    with pytest.raises(InputError):
        load_mkv(p, guitar_idx=0, backing_idx=5)
