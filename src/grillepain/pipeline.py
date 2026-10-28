"""Chaîne d'analyse complète : pistes -> calage -> notes -> forme -> métriques -> Result."""
import sys

from grillepain.audio import Tracks
from grillepain.errors import DetectionError
from grillepain.form import place_notes
from grillepain.metrics import compute
from grillepain.notes import detect_notes
from grillepain.result import Result
from grillepain.theory import parse_grid
from grillepain.timing import align


def _info(msg: str) -> None:
    print(msg, file=sys.stderr)


def run(tracks: Tracks, grid: str, beats_per_bar: int, bpm: float | None,
        downbeat: float | None, min_db: float, file_name: str) -> Result:
    """Analyse deux pistes déjà chargées ; lève GrillepainError en cas d'échec."""
    bars, beat_chords = parse_grid(grid, beats_per_bar)
    _info("Tempo…")
    if downbeat is None:
        _info("Calage de la grille sur l'harmonie…")  # peut être court-circuité par le décompte
    al = align(tracks.backing, beat_chords, bpm, downbeat)
    _info("Détection des notes (≈1 min)…")
    notes = detect_notes(tracks.guitar, min_db)
    if not notes:
        raise DetectionError("aucune note détectée sur la piste guitare")
    placed = place_notes(notes, al, beat_chords, beats_per_bar)
    metrics = compute(placed, al, beat_chords, bars, beats_per_bar)
    return Result(
        input={"file": file_name, "guitar_track": tracks.guitar_name, "backing_track": tracks.backing_name},
        tune={"name": None, "grid": grid, "meter": f"{beats_per_bar}/4", "bars": len(bars)},
        alignment=al, metrics=metrics, notes=placed)
