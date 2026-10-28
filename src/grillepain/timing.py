"""Calage : tempo, décompte, ajustement harmonique de la grille sur le backing."""
from dataclasses import dataclass

import librosa
import numpy as np

from .audio import SR
from .errors import DetectionError, UsageError
from .theory import Chord


@dataclass
class Alignment:
    beats_s: np.ndarray
    period_s: float
    bpm: float
    downbeat_idx: int
    downbeat_s: float
    method: str
    confidence: str  # haute | bonne | moyenne | faible

    @property
    def reliable(self) -> bool:
        return self.confidence != "faible"


def track_beats(backing, bpm_hint):
    hop = 512
    kw = {'start_bpm': bpm_hint} if bpm_hint else {}
    _, frames = librosa.beat.beat_track(y=backing, sr=SR, hop_length=hop, **kw)
    times = librosa.frames_to_time(frames, sr=SR, hop_length=hop)
    if len(times) < 16:
        raise DetectionError("Impossible de détecter le tempo du backing.")
    period = (times[-1] - times[0]) / (len(times) - 1)
    # on prolonge la grille de temps vers le début du fichier
    pre = []
    t = times[0] - period
    while t > -period / 2:
        pre.insert(0, t); t -= period
    return np.r_[pre, times], frames, period


def detect_count_in(backing, period):
    """Clics de décompte : transitoires brefs, isolés, réguliers, avant la musique."""
    hop = 128
    rms = librosa.feature.rms(y=backing, hop_length=hop)[0]
    on = librosa.onset.onset_detect(y=backing, sr=SR, hop_length=hop, units='time', backtrack=True)
    clicks = []
    for o in on[:12]:
        f = librosa.time_to_frames(o, sr=SR, hop_length=hop)
        peak = rms[f:f + 8].max()
        after = rms[f + 20:f + 30].mean() if f + 30 < len(rms) else peak  # ~120-170 ms après
        if peak > 0 and 20 * np.log10(peak / (after + 1e-9)) > 12:
            clicks.append(o)
        else:
            break
    if len(clicks) >= 3:
        d = np.diff(clicks)
        if np.all(np.abs(d - np.median(d)) < 0.08 * np.median(d)):
            return clicks, clicks[-1] + np.median(d)
    return clicks, None


def fit_form(backing, beat_frames, all_beats, beat_chords):
    """Trouve le décalage (en temps) qui aligne la grille sur l'harmonie du backing."""
    hop = 512
    yh = librosa.effects.harmonic(backing)
    ch = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=hop)
    frames = librosa.time_to_frames(all_beats[all_beats >= 0], sr=SR, hop_length=hop)
    cs = librosa.util.sync(ch, frames, aggregate=np.mean)
    cs = cs / (np.linalg.norm(cs, axis=0, keepdims=True) + 1e-9)
    L = len(beat_chords)
    T = np.zeros((L, 12))
    for i, c in enumerate(beat_chords):
        for pc in c.tones:
            T[i, pc] = 1
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    nb = min(cs.shape[1], len(frames))
    first = int(np.sum(all_beats < 0))
    scores = []
    for off in range(L):
        idx = (np.arange(nb) - off) % L
        scores.append(np.mean(np.sum(T[idx] * cs[:, :nb].T, axis=1)))
    scores = np.array(scores)
    best = int(np.argmax(scores))
    second = np.sort(scores)[-2]
    margin = (scores[best] - second) / (np.std(scores) + 1e-9)
    return best + first, margin


def align(backing: np.ndarray, beat_chords: list[Chord], bpm_hint: float | None,
          downbeat_s: float | None) -> Alignment:
    """Trouve le temps 1 du 1er chorus : --downbeat, puis décompte, puis harmonie."""
    if downbeat_s is not None and not 0 <= downbeat_s <= len(backing) / SR:
        raise UsageError(f"--downbeat {downbeat_s} hors de la durée du backing "
                         f"(0 à {len(backing) / SR:.1f} s).")
    beats, frames, period = track_beats(backing, bpm_hint)
    bpm = 60 / period

    if downbeat_s is not None:
        idx = int(np.argmin(np.abs(beats - downbeat_s)))
        method, conf = 'fourni (--downbeat)', 'haute'
    else:
        clicks, start = detect_count_in(backing, period)
        if start is not None:
            idx = int(np.argmin(np.abs(beats - start)))
            method, conf = f'décompte détecté ({len(clicks)} clics)', 'haute'
        else:
            idx, margin = fit_form(backing, frames, beats, beat_chords)
            method = 'ajustement harmonique'
            conf = 'bonne' if margin > 2 else 'moyenne' if margin > 1 else 'faible'
    L = len(beat_chords)
    idx = idx % L  # 1er chorus = le plus tôt possible
    while idx - L >= 0 and beats[idx - L] >= 0:
        idx -= L
    return Alignment(beats, period, bpm, idx, float(beats[idx]), method, conf)
