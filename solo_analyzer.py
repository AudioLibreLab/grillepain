#!/usr/bin/env python3
"""
solo_analyzer.py — analyse d'un solo de guitare enregistré avec JamCapture.

Entrée : un .mkv JamCapture (une piste guitare + une piste backing),
         ou deux fichiers audio (--guitar / --backing).
Sortie : rapport Markdown + JSON détaillé (notes, mesures, accords).

Exemple :
  python3 solo_analyzer.py prise.mkv
  python3 solo_analyzer.py prise.mkv --grid "C7|F7|C7|C7|F7|F7|C7|A7|Dm7|G7|C7 A7|Dm7 G7" --bpm 115
  python3 solo_analyzer.py prise.mkv --downbeat 0.30      # temps 1 du 1er chorus, en secondes

Dépendances : ffmpeg, python3 -m pip install librosa
"""
import argparse, collections, json, os, re, subprocess, sys, tempfile

import numpy as np
import librosa

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
            sys.exit(f"Accord illisible : {sym}")
        q = m.group(2).replace('-', 'm').replace('ø', 'm7b5').replace('°7', 'dim7').replace('Δ', 'maj7')
        q = {'min7': 'm7', 'mi7': 'm7', 'M7': 'maj7', 'o7': 'dim7', '9': '7', '13': '7', '7alt': '7',
             '7b9': '7', '7#9': '7', 'm9': 'm7', 'maj9': 'maj7', '69': '6'}.get(q, q)
        if q not in QUALITIES:
            sys.exit(f"Qualité d'accord non gérée : {sym} (gérées : {', '.join(k or 'maj' for k in QUALITIES)})")
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


# ---------------------------------------------------------------- audio
def extract_tracks(mkv, workdir, gtr_idx=None, bt_idx=None):
    probe = json.loads(subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', mkv],
        capture_output=True, text=True, check=True).stdout)
    audio = [s for s in probe['streams'] if s['codec_type'] == 'audio']
    if len(audio) < 2:
        sys.exit("Le fichier doit contenir au moins 2 pistes audio (guitare + backing).")
    titles = [s.get('tags', {}).get('title', '').lower() for s in audio]
    if gtr_idx is None:
        # heuristique JamCapture : le backing vient du navigateur / lecteur
        player = [i for i, t in enumerate(titles) if any(k in t for k in ('chrome', 'firefox', 'youtube', 'ireal', 'backing', 'spotify'))]
        bt_idx = player[0] if player else 1
        gtr_idx = 0 if bt_idx != 0 else 1
    out = {}
    for name, idx in (('guitar', gtr_idx), ('backing', bt_idx)):
        path = os.path.join(workdir, f'{name}.wav')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mkv, '-map', f'0:a:{idx}',
                        '-ac', '1', '-ar', str(SR), path], check=True)
        out[name] = path
    return out['guitar'], out['backing'], titles[gtr_idx], titles[bt_idx]


def track_beats(backing, bpm_hint):
    hop = 512
    kw = {'start_bpm': bpm_hint} if bpm_hint else {}
    _, frames = librosa.beat.beat_track(y=backing, sr=SR, hop_length=hop, **kw)
    times = librosa.frames_to_time(frames, sr=SR, hop_length=hop)
    if len(times) < 16:
        sys.exit("Impossible de détecter le tempo du backing.")
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


def detect_notes(guitar, min_db):
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
            notes.append({'t': float(a), 'dur': float(e - a), 'midi': p})
    return notes


# ---------------------------------------------------------------- analyse
def analyse(notes, beats, period, downbeat_idx, beat_chords, bars, beats_per_bar, bpm):
    L = len(beat_chords)
    n_bars = len(bars)

    def beatpos(x):
        i = np.searchsorted(beats, x) - 1
        i = int(np.clip(i, 0, len(beats) - 2))
        return i + (x - beats[i]) / (beats[i + 1] - beats[i])

    for n in notes:
        rel = beatpos(n['t']) - downbeat_idx
        n['chorus'] = int(np.floor(rel / L)) + 1
        pos = rel % L
        n['bar'] = int(pos // beats_per_bar) + 1
        n['beat'] = round(float(pos % beats_per_bar), 3)
        c = beat_chords[int(np.floor(pos)) % L]
        n['chord'] = c.sym
        n['name'] = NAMES[n['midi'] % 12]
        n['note'] = librosa.midi_to_note(n['midi'], unicode=False)
        n['function'] = c.function(n['midi'] % 12)
        n['_c'] = c
    notes = [n for n in notes if n['chorus'] >= 1]
    R = {}
    tot = sum(n['dur'] for n in notes) or 1
    pcd = collections.Counter()
    for n in notes:
        pcd[n['name']] += n['dur']
    R['pitch_classes_pct'] = {k: round(100 * v / tot, 1) for k, v in pcd.most_common()}
    # penta mineure de la tonalité (1re racine de la grille)
    key = beat_chords[0].root
    penta = {(key + i) % 12 for i in (0, 3, 5, 7, 10)}
    R['key'] = NAMES[key]
    R['minor_penta_pct'] = round(100 * sum(n['dur'] for n in notes if n['midi'] % 12 in penta) / tot, 1)

    per_chord = {}
    for sym in dict.fromkeys(c.sym for c in beat_chords):
        s = [n for n in notes if n['chord'] == sym]
        if not s:
            continue
        d = sum(n['dur'] for n in s) or 1
        fn = collections.Counter()
        for n in s:
            fn[n['function']] += n['dur']
        strong = [n for n in s if abs(n['beat'] - round(n['beat'])) < 0.2 and round(n['beat']) % 2 == 0]
        per_chord[sym] = {
            'notes': len(s),
            'chord_tones_pct': round(100 * sum(n['dur'] for n in s if n['function'] in n['_c'].tones.values()) / d),
            'guide_tones_pct': round(100 * sum(n['dur'] for n in s if n['function'] in GUIDE) / d),
            'strong_beats_chord_tones_pct': round(100 * sum(n['function'] in n['_c'].tones.values() for n in strong) / max(1, len(strong))),
            'functions_pct': {k: round(100 * v / d) for k, v in fn.most_common()},
            'notes_pct': {k: round(100 * v / d) for k, v in collections.Counter(
                {nm: sum(x['dur'] for x in s if x['name'] == nm) for nm in {x['name'] for x in s}}).most_common(6)},
            'third_count': sum(n['function'] in ('3', 'b3') for n in s),
        }
    R['per_chord'] = per_chord

    # 4te tenue sur dominante
    R['held_4th_on_dominant'] = sum(1 for n in notes if n['_c'].is_dominant() and n['function'] == '11' and n['dur'] > 0.4)

    # notes d'arrivée : 1re note entre -0,5 et +1 temps autour de chaque temps 1
    by = collections.defaultdict(list)
    for n in notes:
        by[(n['chorus'], n['bar'])].append(n)
    choruses = sorted({n['chorus'] for n in notes})
    arrivals, fcount = [], collections.Counter()
    for ch in choruses:
        row = []
        for bar in range(1, n_bars + 1):
            prev = (ch, bar - 1) if bar > 1 else (ch - 1, n_bars)
            cand = [n for n in by[prev] if n['beat'] >= beats_per_bar - 0.5] + \
                   [n for n in by[(ch, bar)] if n['beat'] < 1.0]
            if cand:
                c = Chord(bars[bar - 1][0])
                f = c.function(cand[0]['midi'] % 12)
                row.append(f"{cand[0]['name']}({f})")
                fcount[f] += 1
            else:
                row.append('-')
        arrivals.append({'chorus': ch, 'bars': row})
    R['arrivals'] = arrivals
    R['arrival_functions'] = dict(fcount.most_common())

    # mise en place
    ph = np.array([n['beat'] % 1 for n in notes])
    on = np.array([p if p < 0.5 else p - 1 for p in ph if p < 0.2 or p > 0.8])
    off = np.array([p for p in ph if 0.4 <= p <= 0.8])
    R['timing'] = {
        'on_beat_notes': int(len(on)),
        'mean_offset_ms': round(float(np.mean(on) * period * 1000), 1) if len(on) else None,
        'std_offset_ms': round(float(np.std(on) * period * 1000), 1) if len(on) else None,
        'offbeat_phase_median': round(float(np.median(off)), 3) if len(off) else None,
        'note': "offbeat_phase : 0.50 = croches droites, 0.67 = swing en triolet",
    }
    # silences
    ts = np.array([n['t'] for n in notes]); ends = np.array([n['t'] + n['dur'] for n in notes])
    gaps = ts[1:] - ends[:-1] if len(ts) > 1 else np.array([])
    R['silences'] = {'gt_1_beat': int(np.sum(gaps > period)), 'gt_2_beats': int(np.sum(gaps > 2 * period)),
                     'gt_1_bar': int(np.sum(gaps > beats_per_bar * period))}
    # registre
    m = np.array([n['midi'] for n in notes])
    R['register'] = {'min': librosa.midi_to_note(int(m.min()), unicode=False),
                     'max': librosa.midi_to_note(int(m.max()), unicode=False),
                     'p10': librosa.midi_to_note(int(np.percentile(m, 10)), unicode=False),
                     'p90': librosa.midi_to_note(int(np.percentile(m, 90)), unicode=False)}
    R['per_chorus'] = [{'chorus': ch, 'notes': sum(n['chorus'] == ch for n in notes)} for ch in choruses]
    seq = [n['note'] for n in notes]
    ng = collections.Counter(tuple(seq[i:i + 4]) for i in range(len(seq) - 3))
    R['top_motifs'] = [{'notes': list(k), 'count': v} for k, v in ng.most_common(5) if v > 1]
    for n in notes:
        n.pop('_c', None)
    return R, notes


# ---------------------------------------------------------------- rapport
def report_md(meta, R):
    L = []
    w = L.append
    w(f"# Analyse de solo — {meta['file']}\n")
    w(f"- Grille : `{meta['grid']}`  ({meta['bars']} mesures)")
    w(f"- Tempo : **{meta['bpm']:.1f} bpm** — {len(R['per_chorus'])} chorus analysés")
    w(f"- Temps 1 du 1er chorus : **{meta['downbeat_s']:.2f} s** (méthode : {meta['downbeat_method']}, confiance : {meta['confidence']})")
    w(f"- Pistes : guitare = `{meta['gtr_track']}`, backing = `{meta['bt_track']}`\n")
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
    for a in R['arrivals']:
        w(f"| {a['chorus']} | " + ' | '.join(a['bars']) + " |")
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


def main():
    ap = argparse.ArgumentParser(description="Analyse d'un solo JamCapture")
    ap.add_argument('mkv', nargs='?', help="fichier .mkv JamCapture")
    ap.add_argument('--guitar', help="piste guitare (si pas de mkv)")
    ap.add_argument('--backing', help="piste backing (si pas de mkv)")
    ap.add_argument('--grid', default=C_JAM_BLUES, help="grille, mesures séparées par | (défaut : C Jam Blues)")
    ap.add_argument('--beats-per-bar', type=int, default=4)
    ap.add_argument('--bpm', type=float, help="tempo approximatif (aide la détection)")
    ap.add_argument('--downbeat', type=float, help="temps 1 du premier chorus, en secondes (prioritaire)")
    ap.add_argument('--min-db', type=float, default=-40, help="seuil de niveau des notes guitare (dB / crête)")
    ap.add_argument('-o', '--out', help="préfixe des fichiers de sortie (défaut : à côté de l'entrée)")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        if a.mkv:
            gpath, bpath, gname, bname = extract_tracks(a.mkv, tmp)
            src = a.mkv
        elif a.guitar and a.backing:
            gpath, bpath, gname, bname = a.guitar, a.backing, os.path.basename(a.guitar), os.path.basename(a.backing)
            src = a.guitar
        else:
            ap.error("donner un .mkv, ou --guitar et --backing")
        print("Chargement…", file=sys.stderr)
        g, _ = librosa.load(gpath, sr=SR)
        b, _ = librosa.load(bpath, sr=SR)

    bars, beat_chords = parse_grid(a.grid, a.beats_per_bar)
    print("Tempo…", file=sys.stderr)
    beats, frames, period = track_beats(b, a.bpm)
    bpm = 60 / period

    if a.downbeat is not None:
        idx = int(np.argmin(np.abs(beats - a.downbeat)))
        method, conf = 'fourni (--downbeat)', 'haute'
    else:
        clicks, start = detect_count_in(b, period)
        if start is not None:
            idx = int(np.argmin(np.abs(beats - start)))
            method, conf = f'décompte détecté ({len(clicks)} clics)', 'haute'
        else:
            print("Calage de la grille sur l'harmonie…", file=sys.stderr)
            idx, margin = fit_form(b, frames, beats, beat_chords)
            method = 'ajustement harmonique'
            conf = 'bonne' if margin > 2 else 'moyenne' if margin > 1 else 'faible'
    L = len(beat_chords)
    idx = idx % L  # 1er chorus = le plus tôt possible
    while idx - L >= 0 and beats[idx - L] >= 0:
        idx -= L

    print("Détection des notes (≈1 min)…", file=sys.stderr)
    notes = detect_notes(g, a.min_db)
    R, notes = analyse(notes, beats, period, idx, beat_chords, bars, a.beats_per_bar, bpm)

    meta = {'file': os.path.basename(src), 'grid': a.grid, 'bars': len(bars), 'bpm': bpm,
            'downbeat_s': float(beats[idx]), 'downbeat_method': method, 'confidence': conf,
            'gtr_track': gname, 'bt_track': bname}
    prefix = a.out or os.path.splitext(src)[0]
    md = report_md(meta, R)
    with open(prefix + '_analyse.md', 'w') as f:
        f.write(md)
    with open(prefix + '_analyse.json', 'w') as f:
        json.dump({'meta': meta, 'results': R, 'notes': notes}, f, indent=1, ensure_ascii=False,
                  default=float)
    print(md)
    print(f"→ {prefix}_analyse.md / .json", file=sys.stderr)


if __name__ == '__main__':
    main()
