"""Métriques d'analyse du solo (migration de `analyse()` du prototype)."""
from ..errors import DetectionError
from ..form import PlacedNote
from ..theory import Chord
from ..timing import Alignment
from .arrivals import arrival_metrics
from .motifs import motif_metrics
from .pitch import pitch_metrics
from .rhythm import rhythm_metrics


def compute(notes: list[PlacedNote], al: Alignment, beat_chords: list[Chord],
            bars: list[list[str]], beats_per_bar: int) -> dict:
    """Fusionne les métriques dans l'ordre du prototype."""
    if not notes:
        raise DetectionError("aucune note détectée sur la piste guitare")
    p = pitch_metrics(notes, beat_chords)
    a = arrival_metrics(notes, bars, beats_per_bar)
    r = rhythm_metrics(notes, al.period_s, beats_per_bar)
    order = ['pitch_classes_pct', 'key', 'minor_penta_pct', 'per_chord', 'held_4th_on_dominant']
    R = {k: p[k] for k in order}
    R.update(a)
    R.update(r)
    R['register'] = p['register']
    R['per_chorus'] = p['per_chorus']
    R.update(motif_metrics(notes))
    return R
