"""Théorie : accords, fonctions harmoniques et grille."""
import re

from grillepain.errors import UsageError


SR = 22050
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
ROOTS = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6,
         'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
# qualité -> {intervalle: fonction}
QUALITIES = {
    '7':     {0: 'R', 4: '3', 7: '5', 10: 'b7'},
    'maj7':  {0: 'R', 4: '3', 7: '5', 11: '7'},
    '6':     {0: 'R', 4: '3', 7: '5', 9: '6'},
    '':      {0: 'R', 4: '3', 7: '5'},
    'm7':    {0: 'R', 3: 'b3', 7: '5', 10: 'b7'},
    'm6':    {0: 'R', 3: 'b3', 7: '5', 9: '6'},
    'm':     {0: 'R', 3: 'b3', 7: '5'},
    'mmaj7': {0: 'R', 3: 'b3', 7: '5', 11: '7'},
    'm7b5':  {0: 'R', 3: 'b3', 6: 'b5', 10: 'b7'},
    'dim7':  {0: 'R', 3: 'b3', 6: 'b5', 9: 'bb7'},
}
TENSIONS = {1: 'b9', 2: '9', 3: '#9', 4: 'M3', 5: '11', 6: '#11', 7: '5', 8: 'b13', 9: '13', 10: 'b7', 11: '7M'}
GUIDE = {'3', 'b3', '7', 'b7', 'bb7', '6'}
C_JAM_BLUES = "C7|F7|C7|C7|F7|F7|C7|A7|Dm7|G7|C7 A7|Dm7 G7"


# ---------------------------------------------------------------- accords
class Chord:
    def __init__(self, sym):
        m = re.match(r'^([A-G][b#]?)(.*)$', sym.strip())
        if not m:
            raise UsageError(f"Accord illisible : {sym}")
        q = m.group(2).replace('-', 'm').replace('ø', 'm7b5').replace('°7', 'dim7').replace('Δ', 'maj7')
        q = {'min7': 'm7', 'mi7': 'm7', 'M7': 'maj7', 'o7': 'dim7', '9': '7', '13': '7', '7alt': '7',
             '7b9': '7', '7#9': '7', 'm9': 'm7', 'maj9': 'maj7', '69': '6'}.get(q, q)
        if q not in QUALITIES:
            raise UsageError(f"Qualité d'accord non gérée : {sym} (gérées : {', '.join(k or 'maj' for k in QUALITIES)})")
        self.sym, self.root, self.q = sym.strip(), ROOTS[m.group(1)], q
        self.tones = {(self.root + i) % 12: f for i, f in QUALITIES[q].items()}

    def function(self, pc):
        if pc in self.tones:
            return self.tones[pc]
        return TENSIONS.get((pc - self.root) % 12, '?')

    def is_dominant(self):
        return self.q == '7'


def parse_grid(grid, beats_per_bar):
    bars = [b.split() for b in grid.split('|') if b.strip()]
    beat_chords = []
    for b in bars:
        chords = [Chord(s) for s in b]
        per = beats_per_bar / len(chords)
        for k in range(beats_per_bar):
            beat_chords.append(chords[min(int(k // per), len(chords) - 1)])
    return bars, beat_chords

