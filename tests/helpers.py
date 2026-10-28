"""Aides de test : chaîne complète sur un .mkv avec les défauts du prototype."""
import json
from pathlib import Path

from grillepain.audio import load_mkv
from grillepain.form import place_notes
from grillepain.metrics import compute
from grillepain.notes import detect_notes
from grillepain.result import Result
from grillepain.theory import C_JAM_BLUES, parse_grid
from grillepain.timing import align


def _chain(mkv: Path):
    """Chaîne commune : audio -> timing -> notes -> form -> métriques."""
    tr = load_mkv(mkv)
    bars, beat_chords = parse_grid(C_JAM_BLUES, 4)
    al = align(tr.backing, beat_chords, None, None)
    notes = detect_notes(tr.guitar, -40)
    placed = place_notes(notes, al, beat_chords, 4)
    m = compute(placed, al, beat_chords, bars, 4)
    return tr, bars, al, placed, m


def run_pipeline(mkv: Path) -> dict:
    """Chaîne complète (sans --bpm ni --downbeat, grille par défaut) -> métriques en dict JSON."""
    return json.loads(json.dumps(_chain(mkv)[4], default=float))


def run_result(mkv: Path) -> Result:
    """Chaîne complète -> Result (mêmes défauts que run_pipeline)."""
    tr, bars, al, placed, m = _chain(mkv)
    return Result(
        input={"file": Path(mkv).name, "guitar_track": tr.guitar_name, "backing_track": tr.backing_name},
        tune={"name": None, "grid": C_JAM_BLUES, "meter": "4/4", "bars": len(bars)},
        alignment=al, metrics=m, notes=placed)
