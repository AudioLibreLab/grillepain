"""Métriques de hauteur : classes de hauteur, pentatonique, accords, registre, chorus."""
import collections

import librosa
import numpy as np

from ..form import PlacedNote
from ..theory import GUIDE, NAMES, Chord


def pitch_metrics(notes: list[PlacedNote], beat_chords: list[Chord]) -> dict:
    R: dict = {}
    tot = sum(n.dur_s for n in notes) or 1
    pcd: collections.Counter = collections.Counter()
    for n in notes:
        pcd[n.name] += n.dur_s
    R['pitch_classes_pct'] = {k: round(100 * v / tot, 1) for k, v in pcd.most_common()}
    # penta mineure de la tonalité (1re racine de la grille)
    key = beat_chords[0].root
    penta = {(key + i) % 12 for i in (0, 3, 5, 7, 10)}
    R['key'] = NAMES[key]
    R['minor_penta_pct'] = round(100 * sum(n.dur_s for n in notes if n.midi % 12 in penta) / tot, 1)

    per_chord = {}
    for sym in dict.fromkeys(c.sym for c in beat_chords):
        s = [n for n in notes if n.chord.sym == sym]
        if not s:
            continue
        d = sum(n.dur_s for n in s) or 1
        fn: collections.Counter = collections.Counter()
        for n in s:
            fn[n.function] += n.dur_s
        strong = [n for n in s if abs(n.beat - round(n.beat)) < 0.2 and round(n.beat) % 2 == 0]
        per_chord[sym] = {
            'notes': len(s),
            'chord_tones_pct': round(100 * sum(n.dur_s for n in s if n.function in n.chord.tones.values()) / d),
            'guide_tones_pct': round(100 * sum(n.dur_s for n in s if n.function in GUIDE) / d),
            'strong_beats_chord_tones_pct': round(100 * sum(n.function in n.chord.tones.values() for n in strong) / max(1, len(strong))),
            'functions_pct': {k: round(100 * v / d) for k, v in fn.most_common()},
            'notes_pct': {k: round(100 * v / d) for k, v in collections.Counter(
                {nm: sum(x.dur_s for x in s if x.name == nm) for nm in {x.name for x in s}}).most_common(6)},
            'third_count': sum(n.function in ('3', 'b3') for n in s),
        }
    R['per_chord'] = per_chord

    # 4te tenue sur dominante
    R['held_4th_on_dominant'] = sum(1 for n in notes if n.chord.is_dominant() and n.function == '11' and n.dur_s > 0.4)

    # registre
    m = np.array([n.midi for n in notes])
    R['register'] = {'min': librosa.midi_to_note(int(m.min()), unicode=False),
                     'max': librosa.midi_to_note(int(m.max()), unicode=False),
                     'p10': librosa.midi_to_note(int(np.percentile(m, 10)), unicode=False),
                     'p90': librosa.midi_to_note(int(np.percentile(m, 90)), unicode=False)}
    choruses = sorted({n.chorus for n in notes})
    R['per_chorus'] = [{'chorus': ch, 'notes': sum(n.chorus == ch for n in notes)} for ch in choruses]
    return R
