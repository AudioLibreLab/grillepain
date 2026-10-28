"""Chargement des pistes audio (mkv JamCapture ou paire de fichiers)."""
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

from .errors import InputError

SR = 22050


@dataclass
class Tracks:
    guitar: np.ndarray
    backing: np.ndarray
    guitar_name: str
    backing_name: str
    source: str  # "ireal", "youtube" ou "autre"


def _source(backing_name):
    if "ireal" in backing_name:
        return "ireal"
    if "youtube" in backing_name:
        return "youtube"
    return "autre"


def _charge(path):
    try:
        y, _ = librosa.load(str(path), sr=SR)
    except Exception as e:
        raise InputError(f"Lecture audio impossible : {path} ({e})") from e
    return y


def load_mkv(path, guitar_idx=None, backing_idx=None):
    """Extrait guitare et backing d'un mkv (heuristique sur les titres de pistes)."""
    path = Path(path)
    if not path.is_file():
        raise InputError(f"Fichier introuvable : {path}")
    try:
        probe = json.loads(subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
            capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError) as e:
        raise InputError(f"Lecture des pistes impossible (ffprobe) : {path}") from e
    audio = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    if len(audio) < 2:
        raise InputError("Le fichier doit contenir au moins 2 pistes audio (guitare + backing).")
    titles = [s.get("tags", {}).get("title", "").lower() for s in audio]
    if guitar_idx is None:
        # heuristique JamCapture : le backing vient du navigateur / lecteur
        player = [i for i, t in enumerate(titles)
                  if any(k in t for k in ("chrome", "firefox", "youtube", "ireal", "backing", "spotify"))]
        backing_idx = player[0] if player else 1
        guitar_idx = 0 if backing_idx != 0 else 1
    elif backing_idx is None:
        backing_idx = 1 if guitar_idx != 1 else 0
    for idx in (guitar_idx, backing_idx):
        if not 0 <= idx < len(audio):
            raise InputError(f"Piste audio {idx} inexistante ({len(audio)} pistes).")
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, idx in (("guitar", guitar_idx), ("backing", backing_idx)):
            wav = Path(tmp) / f"{name}.wav"
            try:
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path),
                                "-map", f"0:a:{idx}", "-ac", "1", "-ar", str(SR), str(wav)],
                               capture_output=True, text=True, check=True)
            except (subprocess.CalledProcessError, OSError) as e:
                raise InputError(f"Extraction de la piste {idx} impossible (ffmpeg) : {path}") from e
            out[name] = _charge(wav)
    return Tracks(out["guitar"], out["backing"], titles[guitar_idx], titles[backing_idx],
                  _source(titles[backing_idx]))


def load_pair(guitar, backing):
    """Charge deux fichiers audio séparés (guitare, backing)."""
    guitar, backing = Path(guitar), Path(backing)
    for p in (guitar, backing):
        if not p.is_file():
            raise InputError(f"Fichier introuvable : {p}")
    return Tracks(_charge(guitar), _charge(backing), guitar.name, backing.name, "autre")
