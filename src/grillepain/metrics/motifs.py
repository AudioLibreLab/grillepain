"""Motifs récurrents (4-grammes de notes)."""
import collections

from ..form import PlacedNote


def motif_metrics(notes: list[PlacedNote]) -> dict:
    seq = [n.note for n in notes]
    ng = collections.Counter(tuple(seq[i:i + 4]) for i in range(len(seq) - 3))
    return {'top_motifs': [{'notes': list(k), 'count': v} for k, v in ng.most_common(5) if v > 1]}
