"""Rapport Markdown : même texte que le prototype, lu depuis le Result."""
from ..result import Result


def render(r: Result) -> str:
    R, a = r.metrics, r.alignment
    L: list[str] = []
    w = L.append
    w(f"# Analyse de solo — {r.input['file']}\n")
    w(f"- Grille : `{r.tune['grid']}`  ({r.tune['bars']} mesures)")
    w(f"- Tempo : **{a.bpm:.1f} bpm** — {len(R['per_chorus'])} chorus analysés")
    w(f"- Temps 1 du 1er chorus : **{a.downbeat_s:.2f} s** (méthode : {a.method}, confiance : {a.confidence})")
    w(f"- Pistes : guitare = `{r.input['guitar_track']}`, backing = `{r.input['backing_track']}`\n")
    for warning in r.warnings:  # lignes sans ligne vide ajoutée : le texte hors avertissements reste identique
        w(f"**Attention :** {warning}")
    w("## Notes jouées")
    w(f"- Penta mineure de {R['key']} : **{R['minor_penta_pct']} %** du temps joué")
    w("- Répartition : " + ', '.join(f"{k} {v}%" for k, v in list(R['pitch_classes_pct'].items())[:8]))
    w(f"- Registre : {R['register']['min']} → {R['register']['max']} (80 % des notes entre {R['register']['p10']} et {R['register']['p90']})\n")
    w("## Par accord")
    w("| Accord | Notes | Notes de l'accord | Guide tones | Tierces jouées | Notes principales |")
    w("|---|---|---|---|---|---|")
    for sym, d in R['per_chord'].items():
        w(f"| {sym} | {d['notes']} | {d['chord_tones_pct']} % | {d['guide_tones_pct']} % | {d['third_count']} | "
          + ', '.join(f"{k} {v}%" for k, v in d['notes_pct'].items()) + " |")
    if R['held_4th_on_dominant']:
        w(f"\n4te tenue (> 0,4 s) sur un accord de dominante : **{R['held_4th_on_dominant']} fois**")
    w("\n## Notes d'arrivée (1re note autour du temps 1)")
    nb = len(R['arrivals'][0]['bars'])
    w("| Chorus | " + ' | '.join(str(i) for i in range(1, nb + 1)) + " |")
    w("|---" * (nb + 1) + "|")
    for ar in R['arrivals']:
        w(f"| {ar['chorus']} | " + ' | '.join(ar['bars']) + " |")
    w("\nFonctions d'arrivée : " + ', '.join(f"{k} ×{v}" for k, v in R['arrival_functions'].items()))
    t = R['timing']
    w("\n## Mise en place")
    w(f"- Décalage moyen sur les temps : {t['mean_offset_ms']} ms (négatif = en avance), dispersion ±{t['std_offset_ms']} ms")
    w(f"- Croches : phase médiane {t['offbeat_phase_median']} (0,50 droit · 0,67 swing)")
    s = R['silences']
    w(f"- Silences : {s['gt_1_beat']} > 1 temps, {s['gt_2_beats']} > 2 temps, {s['gt_1_bar']} > 1 mesure\n")
    if R['top_motifs']:
        w("## Motifs répétés (4 notes)")
        for m in R['top_motifs']:
            w(f"- {' '.join(m['notes'])} ×{m['count']}")
    w("\n_Précision : hauteurs fiables ; timing ±20 ms ; si la confiance du calage est faible, "
      "les arrivées peuvent être décalées — relancer avec --downbeat._")
    return '\n'.join(L) + '\n'
