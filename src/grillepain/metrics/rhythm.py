"""Mise en place (décalage au temps) et silences."""
import numpy as np

from ..form import PlacedNote


def rhythm_metrics(notes: list[PlacedNote], period_s: float, beats_per_bar: int) -> dict:
    period = period_s
    R: dict = {}
    ph = np.array([n.beat % 1 for n in notes])
    on = np.array([p if p < 0.5 else p - 1 for p in ph if p < 0.2 or p > 0.8])
    off = np.array([p for p in ph if 0.4 <= p <= 0.8])
    R['timing'] = {
        'on_beat_notes': int(len(on)),
        'mean_offset_ms': round(float(np.mean(on) * period * 1000), 1) if len(on) else None,
        'std_offset_ms': round(float(np.std(on) * period * 1000), 1) if len(on) else None,
        'offbeat_phase_median': round(float(np.median(off)), 3) if len(off) else None,
        'note': "offbeat_phase : 0.50 = croches droites, 0.67 = swing en triolet",
    }
    # silences
    ts = np.array([n.t_s for n in notes]); ends = np.array([n.t_s + n.dur_s for n in notes])
    gaps = ts[1:] - ends[:-1] if len(ts) > 1 else np.array([])
    R['silences'] = {'gt_1_beat': int(np.sum(gaps > period)), 'gt_2_beats': int(np.sum(gaps > 2 * period)),
                     'gt_1_bar': int(np.sum(gaps > beats_per_bar * period))}
    return R
