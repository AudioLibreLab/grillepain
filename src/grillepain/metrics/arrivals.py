"""Notes d'arrivée sur le temps 1 de chaque mesure."""
import collections

from ..form import PlacedNote
from ..theory import Chord


def arrival_metrics(notes: list[PlacedNote], bars: list[list[str]], beats_per_bar: int) -> dict:
    """1re note entre -0,5 et +1 temps autour de chaque temps 1."""
    n_bars = len(bars)
    by: collections.defaultdict = collections.defaultdict(list)
    for n in notes:
        by[(n.chorus, n.bar)].append(n)
    choruses = sorted({n.chorus for n in notes})
    arrivals, fcount = [], collections.Counter()
    for ch in choruses:
        row = []
        for bar in range(1, n_bars + 1):
            prev = (ch, bar - 1) if bar > 1 else (ch - 1, n_bars)
            cand = [n for n in by[prev] if n.beat >= beats_per_bar - 0.5] + \
                   [n for n in by[(ch, bar)] if n.beat < 1.0]
            if cand:
                c = Chord(bars[bar - 1][0])
                f = c.function(cand[0].midi % 12)
                row.append(f"{cand[0].name}({f})")
                fcount[f] += 1
            else:
                row.append('-')
        arrivals.append({'chorus': ch, 'bars': row})
    return {'arrivals': arrivals, 'arrival_functions': dict(fcount.most_common())}
