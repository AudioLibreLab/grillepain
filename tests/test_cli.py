import dataclasses
import json

import pytest

from helpers import make_take

from grillepain import pipeline
from grillepain.cli import main


def test_end_to_end(tmp_path):
    p = tmp_path / "ma prise é.mkv"
    make_take(p, count_in=True)
    assert main(["analyse", str(p), "--quiet"]) == 0
    d = json.loads((tmp_path / "ma prise é_analyse.json").read_text(encoding="utf-8"))
    assert d["schema_version"] == "1.0.0" and d["alignment"]["reliable"] is True
    assert (tmp_path / "ma prise é_analyse.md").exists()


def test_silent_guitar_exit_5(tmp_path, capsys):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True, guitar_silent=True)
    assert main(["analyse", str(p), "--quiet"]) == 5
    assert "aucune note" in capsys.readouterr().err
    assert not (tmp_path / "x_analyse.md").exists() and not (tmp_path / "x_analyse.json").exists()


def test_missing_file_exit_4(tmp_path):
    assert main(["analyse", str(tmp_path / "absent.mkv")]) == 4


def test_bad_grid_exit_2(tmp_path):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True)
    assert main(["analyse", str(p), "--grid", "C7|H7"]) == 2


def test_low_confidence_exit_3(tmp_path, monkeypatch):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True)
    real_align = pipeline.align
    monkeypatch.setattr(pipeline, "align",
                        lambda *a, **k: dataclasses.replace(real_align(*a, **k), confidence="faible"))
    assert main(["analyse", str(p), "--quiet"]) == 3
    assert (tmp_path / "x_analyse.md").exists() and (tmp_path / "x_analyse.json").exists()


@pytest.mark.parametrize("opts", [["--grid", ""], ["--grid", "|"], ["--beats-per-bar", "0"], ["--bpm", "-10"]])
def test_usage_errors_exit_2(tmp_path, capsys, opts):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True)
    assert main(["analyse", str(p), "--quiet", *opts]) == 2
    assert "grillepain :" in capsys.readouterr().err


def test_unwritable_output_exit_4(tmp_path, capsys):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True)
    assert main(["analyse", str(p), "--quiet", "-o", str(tmp_path / "nope" / "x")]) == 4
    assert "Écriture impossible" in capsys.readouterr().err


def test_mkv_and_pair_exclusive(tmp_path):
    with pytest.raises(SystemExit) as e:
        main(["analyse", str(tmp_path / "x.mkv"), "--guitar", "g.wav", "--backing", "b.wav"])
    assert e.value.code == 2
