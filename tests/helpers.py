"""Aides de test : chaîne complète sur un .mkv avec les défauts du prototype."""
import json
from pathlib import Path

from grillepain.audio import load_mkv
from grillepain.form import place_notes
from grillepain.metrics import compute
from grillepain.notes import detect_notes
from grillepain.theory import C_JAM_BLUES, parse_grid
from grillepain.timing import align


def run_pipeline(mkv: Path) -> dict:
    """audio -> timing -> notes -> form -> métriques (sans --bpm ni --downbeat, grille par défaut)."""
    tr = load_mkv(mkv)
    bars, beat_chords = parse_grid(C_JAM_BLUES, 4)
    al = align(tr.backing, beat_chords, None, None)
    notes = detect_notes(tr.guitar, -40)
    placed = place_notes(notes, al, beat_chords, 4)
    m = compute(placed, al, beat_chords, bars, 4)
    return json.loads(json.dumps(m, default=float))
