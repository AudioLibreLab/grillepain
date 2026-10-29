"""Placement des notes dans la forme (chorus, mesure, temps, accord, fonction)."""
from dataclasses import dataclass

import librosa
import numpy as np

from .notes import Note
from .theory import NAMES, Chord
from .timing import Alignment


@dataclass
class PlacedNote:
    t_s: float
    dur_s: float
    midi: int
    level_db: float
    chorus: int
    bar: int
    beat: float
    chord: Chord
    name: str
    note: str
    function: str

    def to_dict(self) -> dict:
        """Dictionnaire à plat ; l'accord est sérialisé par son symbole."""
        d = {f: getattr(self, f) for f in self.__dataclass_fields__}
        d["chord"] = self.chord.sym
        return d


def place_notes(notes: list[Note], al: Alignment, beat_chords: list[Chord],
                beats_per_bar: int) -> list[PlacedNote]:
    """Place chaque note dans la forme ; écarte celles avant le chorus 1."""
    beats = al.beats_s
    L = len(beat_chords)

    def beatpos(x: float) -> float:
        i = np.searchsorted(beats, x) - 1
        i = int(np.clip(i, 0, len(beats) - 2))
        return i + (x - beats[i]) / (beats[i + 1] - beats[i])

    placed = []
    for n in notes:
        rel = beatpos(n.t_s) - al.downbeat_idx
        chorus = int(np.floor(rel / L)) + 1
        if chorus < 1:
            continue
        pos = rel % L
        c = beat_chords[int(np.floor(pos)) % L]
        placed.append(PlacedNote(
            t_s=n.t_s, dur_s=n.dur_s, midi=n.midi, level_db=n.level_db,
            chorus=chorus, bar=int(pos // beats_per_bar) + 1,
            beat=round(float(pos % beats_per_bar), 3), chord=c,
            name=NAMES[n.midi % 12], note=librosa.midi_to_note(n.midi, unicode=False),
            function=c.function(n.midi % 12)))
    return placed
