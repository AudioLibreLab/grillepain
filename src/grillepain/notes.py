"""Détection des notes de la guitare (pyin + onsets)."""
from dataclasses import dataclass

import librosa
import numpy as np

from .audio import SR


@dataclass
class Note:
    t_s: float
    dur_s: float
    midi: int
    level_db: float


def detect_notes(guitar, min_db=-40):
    hop = 256
    f0, voiced, _ = librosa.pyin(guitar, fmin=75, fmax=1400, sr=SR, frame_length=2048, hop_length=hop)
    t = np.arange(len(f0)) * hop / SR
    midi = 69 + 12 * np.log2(f0 / 440.0)
    onsets = librosa.onset.onset_detect(y=guitar, sr=SR, hop_length=hop, units='time')
    ref = np.max(np.abs(guitar)) + 1e-9
    notes = []
    for a, e in zip(onsets, list(onsets[1:]) + [t[-1]]):
        m = (t >= a + 0.03) & (t < min(e, a + 0.25)) & voiced
        if m.sum() < 3 or np.nanstd(midi[m]) > 1.0:
            continue
        seg = guitar[int(a * SR):int((a + 0.15) * SR)]
        db = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) / ref + 1e-9)
        if db < min_db:
            continue
        p = int(round(np.nanmedian(midi[m])))
        if 40 <= p <= 90:
            notes.append(Note(t_s=float(a), dur_s=float(e - a), midi=p, level_db=float(db)))
    return notes
