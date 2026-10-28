"""Générateurs d'audio synthétique pour les tests (indépendants de grillepain)."""
import subprocess
import wave

import numpy as np

SR = 22050
_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_QUALITES = {"7": (0, 4, 7, 10), "m7": (0, 3, 7, 10), "maj7": (0, 4, 7, 11)}


def _norm(y, peak=0.9):
    m = np.max(np.abs(y)) if len(y) else 0
    return (y * (peak / m) if m > peak else y).astype(np.float32)


def _mix(y, x, t_s):
    """Ajoute x dans y à partir de t_s (tronqué à la fin de y)."""
    i = int(round(t_s * SR))
    n = max(0, min(len(x), len(y) - i))
    if n:
        y[i:i + n] += x[:n]


def silence(dur_s):
    return np.zeros(int(round(dur_s * SR)), dtype=np.float32)


def _click():
    t = np.arange(int(0.015 * SR)) / SR
    return 0.8 * np.sin(2 * np.pi * 2000 * t) * np.exp(-t / 0.004)


def click_track(times_s, dur_s):
    y = np.zeros(int(round(dur_s * SR)))
    for t in times_s:
        _mix(y, _click(), t)
    return _norm(y)


def _pluck(midi, dur_s, amp=1.0):
    f = 440 * 2 ** ((midi - 69) / 12)
    t = np.arange(int(round(dur_s * SR))) / SR
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3, 4))
    env = np.minimum(t / 0.005, 1) * np.exp(-t / 0.6)  # attaque 5 ms
    return amp * y * env / 2


def pluck(midi, dur_s):
    return _norm(_pluck(midi, dur_s))


def melody(notes, dur_s):
    y = np.zeros(int(round(dur_s * SR)))
    for t, d, midi in notes:
        x = _pluck(midi, d)
        x *= np.minimum(np.arange(len(x), 0, -1) / (0.05 * SR), 1)  # relâchement 50 ms (évite l'onset parasite de la coupure)
        _mix(y, x, t)
    return _norm(y)


def _accord(symbole):
    """'Bb7' -> (pc fondamentale, intervalles). Qualités 7, m7, maj7."""
    pc = _PC[symbole[0]]
    reste = symbole[1:]
    while reste[:1] in ("b", "#"):
        pc += -1 if reste[0] == "b" else 1
        reste = reste[1:]
    return pc % 12, _QUALITES[reste]


def chord_backing(grid, bpm, beats_per_bar, start_s, choruses, count_in):
    beat = 60.0 / bpm
    # un accord par temps, comme parse_grid (plusieurs accords par mesure : partage égal)
    accords = []
    for mesure in grid.split("|"):
        syms = mesure.split()
        accords += [_accord(syms[i * len(syms) // beats_per_bar]) for i in range(beats_per_bar)]
    n_beats = len(accords) * choruses
    y = np.zeros(int(round((start_s + n_beats * beat + 1.0) * SR)))
    for b in range(n_beats):
        root, ivs = accords[b % len(accords)]
        t0 = start_s + b * beat
        _mix(y, _pluck(36 + root, beat, 1.0), t0)  # basse, octave 2
        if b == 0 or accords[b % len(accords)] != accords[(b - 1) % len(accords)]:
            # accord tenu jusqu'au prochain changement
            n = 1
            while n < len(accords) and accords[(b + n) % len(accords)] == accords[b % len(accords)] and b + n < n_beats:
                n += 1
            d = beat * n
            t = np.arange(int(round(d * SR))) / SR
            env = np.minimum(t / 0.02, 1) * np.minimum((d - t) / 0.05, 1)
            for iv in ivs:
                f = 440 * 2 ** ((48 + root + iv - 69) / 12)  # octave 3
                _mix(y, 0.12 * np.sin(2 * np.pi * f * t) * env, t0)
    if count_in:  # 4 clics sur les temps précédant start_s
        for k in range(4):
            _mix(y, _click(), start_s - (4 - k) * beat)
    return _norm(y)


def write_wav(path, y):
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def make_mkv(path, guitar, backing, titles=("carla", "chrome")):
    """MKV à deux pistes audio FLAC (guitare, backing) via ffmpeg."""
    wavs = [path.with_name(f"{path.stem}_{i}.wav") for i in range(2)]
    for w, y in zip(wavs, (guitar, backing)):
        write_wav(w, y)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wavs[0]), "-i", str(wavs[1]),
           "-map", "0:a", "-map", "1:a", "-c:a", "flac"]
    for i, titre in enumerate(titles):
        cmd += [f"-metadata:s:a:{i}", f"title={titre}"]
    subprocess.run(cmd + [str(path)], check=True)
    for w in wavs:
        w.unlink()
