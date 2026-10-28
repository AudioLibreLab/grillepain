import dataclasses
import json

from helpers import make_take

from grillepain import pipeline
from grillepain.cli import main


def test_end_to_end(tmp_path):
    p = tmp_path / "ma prise é.mkv"
    make_take(p, count_in=True)
    assert main(["analyse", str(p), "--quiet"]) == 0
    d = json.load(open(tmp_path / "ma prise é_analyse.json", encoding="utf-8"))
    assert d["schema_version"] == "1.0.0" and d["alignment"]["reliable"] is True
    assert (tmp_path / "ma prise é_analyse.md").exists()


def test_silent_guitar_exit_5(tmp_path, capsys):
    p = tmp_path / "x.mkv"
    make_take(p, count_in=True, guitar_silent=True)
    assert main(["analyse", str(p), "--quiet"]) == 5
    assert "aucune note" in capsys.readouterr().err


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
