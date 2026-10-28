# grillepain phase 1 — package, migration, JSON versionné — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer `solo_analyzer.py` en package `grillepain` (uv, CLI, tests) sans changer les
résultats d'analyse, puis produire un JSON à schéma versionné et des codes retour exploitables par
JamCapture.

**Architecture:** Découpage du prototype en modules à entrée/sortie typées (`audio` → `timing` →
`notes` → `form` → `metrics` → `result` → `report`). Seuls `audio.py` et `cli.py` touchent au
système de fichiers et à ffmpeg. Les erreurs sont des exceptions typées portant leur code retour ;
seul `cli.main()` les convertit en code de sortie.

**Tech Stack:** Python ≥ 3.11, uv, librosa, numpy, ffmpeg/ffprobe (système), pytest, jsonschema (dev).

**Spec:** `docs/superpowers/specs/2026-10-28-grillepain-design.md` (étapes 1 et 2 du §10).
Hors de ce plan : grilles YAML, import iReal, `eval`, calage robuste, métriques de forme,
conseils, SQLite, HTML (plans suivants).

## Global Constraints

- Linux, Python ≥ 3.11, `uv`, librosa, ffmpeg. Pas de GPU.
- Taux d'échantillonnage d'analyse : `SR = 22050` (inchangé).
- Messages utilisateur et rapport en français.
- Précision annoncée : hauteurs fiables, timing ±20 ms.
- Les fichiers audio ne sont pas versionnés ; les tests génèrent leur audio (`tests/synth.py`) ou
  sont marqués `golden` et sautés si `examples/MySong_20261027_183119.mkv` est absent.
- Codes retour : 0 = OK calage fiable · 3 = OK calage peu fiable · 2 = erreur d'usage ·
  4 = fichier illisible / pistes introuvables · 5 = tempo ou notes non détectés.
- `schema_version` du JSON : `"1.0.0"`.
- Non-régression : sur la prise d'exemple, les métriques sont identiques à celles du prototype.

## Review Focus

1. Guitare silencieuse ou trop faible (aucune note) → le prototype plante sur `m.min()` ;
   attendu : code 5, message « aucune note détectée sur la piste guitare ». Test : Task 11.
2. `.mkv` à une seule piste audio, ou fichier inexistant → code 4, message clair. Test : Task 4.
3. Backing trop court / sans pulsation (< 16 temps) → code 5, pas de traceback. Test : Task 5.
4. Mesure à 3 temps avec deux accords (`--beats-per-bar 3`, `"C7 A7"`) → C7 sur les temps 1-2,
   A7 sur le temps 3 (comportement du prototype, figé). Test : Task 3.
5. Nom de fichier avec espaces et accents (`ma prise é.mkv`) → analyse OK, sorties
   `ma prise é_analyse.md/.json` à côté. Test : Task 11.

---

### Task 1: Squelette uv, CLI vide, référence du prototype

**Files:**
- Create: `pyproject.toml`, `src/grillepain/__init__.py`, `src/grillepain/__main__.py`,
  `src/grillepain/cli.py`, `tests/conftest.py`, `tests/test_cli_smoke.py`
- Create (fichier de référence, versionné) : `examples/MySong_20261027_183119_prototype.json`

**Interfaces:**
- Produces: commande `grillepain` → `grillepain.cli:main(argv: list[str] | None = None) -> int` ;
  `grillepain.__version__ = "0.1.0"` ; marqueur pytest `golden` ; fixture
  `example_mkv: pathlib.Path` (skip si absent).

- [ ] **Step 1:** Installer uv s'il manque (`curl -LsSf https://astral.sh/uv/install.sh | sh`,
  demander à l'utilisateur), puis `uv init --package --name grillepain` adapté à la structure
  ci-dessus ; dépendances `librosa`, `numpy` ; dev : `pytest`, `jsonschema` ;
  `[project.scripts] grillepain = "grillepain.cli:main"` ; `requires-python = ">=3.11"`.
- [ ] **Step 2: Générer la référence du prototype**

  Run: `uv run python solo_analyzer.py examples/MySong_20261027_183119.mkv -o /tmp/ref`
  puis copier `/tmp/ref_analyse.json` vers `examples/MySong_20261027_183119_prototype.json`
  et vérifier que `/tmp/ref_analyse.md` est identique à `examples/MySong_20261027_183119_analyse.md`
  (`diff` vide). Si le diff n'est pas vide, s'arrêter et le signaler (prototype non déterministe).
- [ ] **Step 3: Test qui échoue**

```python
def test_help_runs(capsys):
    from grillepain.cli import main
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    assert "analyse" in capsys.readouterr().out
```

- [ ] **Step 4:** `uv run pytest tests/test_cli_smoke.py -v` → FAIL (module absent).
- [ ] **Step 5:** `cli.main` avec argparse et un sous-parseur `analyse` (sans action pour l'instant).
  `conftest.py` : enregistrer le marqueur `golden` et la fixture `example_mkv`.
- [ ] **Step 6:** `uv run pytest -v` → PASS. `uv run grillepain --help` affiche l'aide.
- [ ] **Step 7:** Commit `feat: squelette uv et référence du prototype`.

### Task 2: Générateurs d'audio synthétique

**Files:**
- Create: `tests/synth.py`, `tests/test_synth.py`

**Interfaces:**
- Produces (tous à `sr=22050`, mono `np.float32`, valeurs dans [-1, 1]) :
  - `silence(dur_s: float) -> np.ndarray`
  - `click_track(times_s: list[float], dur_s: float) -> np.ndarray` — clic 2 kHz, 15 ms, décroissance exponentielle.
  - `pluck(midi: int, dur_s: float) -> np.ndarray` — harmoniques 1-4, attaque 5 ms, décroissance.
  - `melody(notes: list[tuple[float, float, int]], dur_s: float) -> np.ndarray` — (t_s, dur_s, midi).
  - `chord_backing(grid: str, bpm: float, beats_per_bar: int, start_s: float, choruses: int, count_in: bool) -> np.ndarray`
    — accords tenus (notes de l'accord en octave 3-4 + fondamentale en octave 2), une attaque de
    basse par temps ; si `count_in`, 4 clics aux temps précédant `start_s`.
  - `write_wav(path, y)` et `make_mkv(path, guitar, backing, titles=("carla", "chrome"))` (ffmpeg, FLAC).

- [ ] **Step 1: Tests qui échouent**

```python
def test_pluck_pitch():
    y = synth.pluck(60, 1.0)
    f0, *_ = librosa.pyin(y, fmin=75, fmax=1400, sr=22050)
    assert abs(np.nanmedian(69 + 12 * np.log2(f0 / 440)) - 60) < 0.3

def test_backing_length_and_count_in():
    y = synth.chord_backing("C7|F7", bpm=120, beats_per_bar=4, start_s=2.0, choruses=2, count_in=True)
    assert len(y) >= int((2.0 + 16 * 0.5) * 22050)
    on = librosa.onset.onset_detect(y=y, sr=22050, units="time")
    assert abs(on[0] - 0.0) < 0.02 and abs(on[3] - 1.5) < 0.02

def test_make_mkv(tmp_path):
    p = tmp_path / "x.mkv"
    synth.make_mkv(p, synth.silence(1), synth.silence(1))
    assert p.exists() and p.stat().st_size > 0
```

- [ ] **Step 2:** `uv run pytest tests/test_synth.py -v` → FAIL.
- [ ] **Step 3:** Implémenter `tests/synth.py` sans importer `grillepain` (la vérité des tests doit
  être indépendante du code testé) : parsing local de la grille, qualités `7`, `m7`, `maj7` seulement.
- [ ] **Step 4:** `uv run pytest tests/test_synth.py -v` → PASS.
- [ ] **Step 5:** Commit `test: générateurs d'audio synthétique`.

### Task 3: Théorie (accords, grille) et erreurs typées

**Files:**
- Create: `src/grillepain/errors.py`, `src/grillepain/theory.py`, `tests/test_theory.py`

**Interfaces:**
- Produces:
  - `errors.GrillepainError(Exception)` avec attribut de classe `exit_code: int` ;
    sous-classes `UsageError` (2), `InputError` (4), `DetectionError` (5).
  - `theory.NAMES`, `ROOTS`, `QUALITIES`, `TENSIONS`, `GUIDE`, `C_JAM_BLUES` (valeurs du prototype).
  - `theory.Chord(sym: str)` : `.sym`, `.root`, `.q`, `.tones: dict[int, str]`,
    `.function(pc: int) -> str`, `.is_dominant() -> bool`. Accord illisible ou qualité non gérée
    → `UsageError` (même texte que le prototype, plus de `sys.exit`).
  - `theory.parse_grid(grid: str, beats_per_bar: int) -> tuple[list[list[str]], list[Chord]]`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_functions():
    assert Chord("C7").function(10) == "b7"
    assert Chord("Dm7").function(5) == "b3"
    assert Chord("C7").function(3) == "#9"
    assert Chord("D-7").q == "m7" and Chord("Bbmaj7").root == 10

def test_bad_chords():
    with pytest.raises(UsageError):
        Chord("H7")
    with pytest.raises(UsageError):
        Chord("C7sus4")

def test_two_chords_in_3_4():
    bars, beats = parse_grid("C7 A7|Dm7", 3)
    assert [c.sym for c in beats] == ["C7", "C7", "A7", "Dm7", "Dm7", "Dm7"]

def test_blues_grid():
    bars, beats = parse_grid(C_JAM_BLUES, 4)
    assert len(bars) == 12 and len(beats) == 48 and beats[42].sym == "A7"
```

- [ ] **Step 2:** `uv run pytest tests/test_theory.py -v` → FAIL.
- [ ] **Step 3:** Déplacer `Chord`, `parse_grid` et constantes du prototype ; remplacer `sys.exit` par `UsageError`.
- [ ] **Step 4:** `uv run pytest tests/test_theory.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: module theory et erreurs typées`.

### Task 4: Audio (pistes du mkv)

**Files:**
- Create: `src/grillepain/audio.py`, `tests/test_audio.py`

**Interfaces:**
- Consumes: `errors.InputError`, `tests.synth.make_mkv`.
- Produces:
  - `audio.SR = 22050`
  - `@dataclass Tracks: guitar: np.ndarray, backing: np.ndarray, guitar_name: str, backing_name: str, source: str`
  - `audio.load_mkv(path: Path, guitar_idx: int | None = None, backing_idx: int | None = None) -> Tracks`
    (heuristique de titres du prototype ; extraction ffmpeg dans un `TemporaryDirectory`).
  - `audio.load_pair(guitar: Path, backing: Path) -> Tracks`
  - Fichier absent, ffprobe en échec ou < 2 pistes audio → `InputError`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_titles_heuristic(tmp_path):
    g = synth.pluck(60, 1.0); b = synth.silence(1.0)
    p = tmp_path / "ma prise é.mkv"
    synth.make_mkv(p, guitar=b, backing=g, titles=("chrome", "carla"))  # ordre inversé
    t = load_mkv(p)
    assert t.guitar_name == "carla" and t.backing_name == "chrome"
    assert np.abs(t.guitar).max() > 0.1

def test_missing_file(tmp_path):
    with pytest.raises(InputError):
        load_mkv(tmp_path / "absent.mkv")

def test_single_track(tmp_path):
    p = tmp_path / "mono.mkv"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=d=1", "-c:a", "flac", str(p)], check=True)
    with pytest.raises(InputError, match="2 pistes"):
        load_mkv(p)
```

- [ ] **Step 2:** `uv run pytest tests/test_audio.py -v` → FAIL.
- [ ] **Step 3:** Implémenter à partir de `extract_tracks` + `librosa.load(sr=SR)`.
- [ ] **Step 4:** `uv run pytest tests/test_audio.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: module audio`.

### Task 5: Calage (tempo, décompte, ajustement harmonique)

**Files:**
- Create: `src/grillepain/timing.py`, `tests/test_timing.py`

**Interfaces:**
- Consumes: `theory.Chord`, `errors.DetectionError`, `errors.UsageError`.
- Produces:
  - `@dataclass Alignment: beats_s: np.ndarray, period_s: float, bpm: float, downbeat_idx: int, downbeat_s: float, method: str, confidence: str`
    avec `confidence ∈ {"haute", "bonne", "moyenne", "faible"}` et propriété
    `reliable -> bool` (= `confidence != "faible"`).
  - `timing.align(backing: np.ndarray, beat_chords: list[Chord], bpm_hint: float | None, downbeat_s: float | None) -> Alignment`
    — logique exacte de `main()` du prototype (priorité `--downbeat` → décompte → ajustement
    harmonique, puis ramener au 1er chorus possible). Fonctions internes `track_beats`,
    `detect_count_in`, `fit_form` copiées telles quelles.
  - < 16 temps détectés → `DetectionError("Impossible de détecter le tempo du backing.")` ;
    `downbeat_s` hors de `[0, durée]` → `UsageError`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_count_in_downbeat():
    y = synth.chord_backing(C_JAM_BLUES, bpm=120, beats_per_bar=4, start_s=2.0, choruses=2, count_in=True)
    _, beats = parse_grid(C_JAM_BLUES, 4)
    a = align(y, beats, bpm_hint=120, downbeat_s=None)
    assert a.method.startswith("décompte") and a.confidence == "haute"
    assert abs(a.downbeat_s - 2.0) < 0.02 and abs(a.bpm - 120) < 1

def test_harmonic_fit_without_count_in():
    y = synth.chord_backing(C_JAM_BLUES, bpm=120, beats_per_bar=4, start_s=1.0, choruses=3, count_in=False)
    _, beats = parse_grid(C_JAM_BLUES, 4)
    a = align(y, beats, bpm_hint=120, downbeat_s=None)
    assert a.method == "ajustement harmonique"
    assert abs(a.downbeat_s - 1.0) < 0.02

def test_manual_downbeat():
    y = synth.chord_backing("C7|F7", bpm=120, beats_per_bar=4, start_s=0.5, choruses=8, count_in=False)
    _, beats = parse_grid("C7|F7", 4)
    a = align(y, beats, bpm_hint=None, downbeat_s=0.5)
    assert a.confidence == "haute" and abs(a.downbeat_s - 0.5) < 0.02

def test_no_pulse():
    with pytest.raises(DetectionError):
        align(synth.silence(3.0), parse_grid("C7", 4)[1], None, None)
```

- [ ] **Step 2:** `uv run pytest tests/test_timing.py -v` → FAIL.
- [ ] **Step 3:** Implémenter. Si `test_harmonic_fit_without_count_in` échoue avec un décalage
  de 4 ou 8 temps, ajuster le générateur (basse plus marquée) et non l'algorithme : ce plan
  ne change pas le comportement du calage.
- [ ] **Step 4:** `uv run pytest tests/test_timing.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: module timing (calage du temps 1)`.

### Task 6: Détection des notes

**Files:**
- Create: `src/grillepain/notes.py`, `tests/test_notes.py`

**Interfaces:**
- Produces: `@dataclass Note: t_s: float, dur_s: float, midi: int, level_db: float` ;
  `notes.detect_notes(guitar: np.ndarray, min_db: float = -40) -> list[Note]` (algorithme du prototype ;
  `level_db` = le `db` déjà calculé).

- [ ] **Step 1: Test qui échoue**

```python
def test_detects_melody():
    truth = [(0.5, 0.4, 60), (1.0, 0.4, 64), (1.5, 0.4, 67), (2.0, 0.8, 70)]
    notes = detect_notes(synth.melody(truth, 3.0))
    assert [n.midi for n in notes] == [60, 64, 67, 70]
    assert all(abs(n.t_s - t) < 0.02 for n, (t, _, _) in zip(notes, truth))

def test_silence_gives_no_notes():
    assert detect_notes(synth.silence(2.0)) == []
```

- [ ] **Step 2:** `uv run pytest tests/test_notes.py -v` → FAIL.
- [ ] **Step 3:** Implémenter (copie de `detect_notes`, sortie en `Note`).
- [ ] **Step 4:** `uv run pytest tests/test_notes.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: module notes`.

### Task 7: Placement dans la forme

**Files:**
- Create: `src/grillepain/form.py`, `tests/test_form.py`

**Interfaces:**
- Consumes: `Note`, `Alignment`, `Chord`.
- Produces:
  - `@dataclass PlacedNote: t_s, dur_s, midi, level_db, chorus: int, bar: int, beat: float, chord: Chord, name: str, note: str, function: str`
    et `to_dict() -> dict` (chord sérialisé par son symbole).
  - `form.place_notes(notes: list[Note], al: Alignment, beat_chords: list[Chord], beats_per_bar: int) -> list[PlacedNote]`
    — logique du début de `analyse()` (`beatpos`, chorus/bar/beat arrondi à 3 décimales) ;
    les notes avant le chorus 1 sont écartées.

- [ ] **Step 1: Test qui échoue**

```python
def test_placement():
    beats = np.arange(0, 60, 0.5)
    al = Alignment(beats_s=beats, period_s=0.5, bpm=120, downbeat_idx=2, downbeat_s=1.0, method="m", confidence="haute")
    _, bc = parse_grid(C_JAM_BLUES, 4)
    notes = [Note(0.2, 0.2, 60, -10), Note(1.0, 0.3, 64, -10), Note(1.0 + 4 * 2 + 0.25, 0.3, 70, -10),
             Note(1.0 + 48 * 0.5, 0.3, 60, -10)]
    p = place_notes(notes, al, bc, 4)
    assert len(p) == 3                                   # la note d'intro est écartée
    assert (p[0].chorus, p[0].bar, p[0].beat, p[0].chord.sym, p[0].function) == (1, 1, 0.0, "C7", "3")
    assert (p[1].bar, p[1].beat, p[1].chord.sym, p[1].function) == (5, 0.5, "F7", "11")  # Bb sur F7
    assert (p[2].chorus, p[2].bar) == (2, 1)
```

- [ ] **Step 2:** `uv run pytest tests/test_form.py -v` → FAIL.
- [ ] **Step 3:** Implémenter.
- [ ] **Step 4:** `uv run pytest tests/test_form.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: placement des notes dans la forme`.

### Task 8: Métriques (migration de `analyse()`)

**Files:**
- Create: `src/grillepain/metrics/__init__.py`, `metrics/pitch.py`, `metrics/arrivals.py`,
  `metrics/rhythm.py`, `metrics/motifs.py`, `tests/test_metrics.py`

**Interfaces:**
- Consumes: `PlacedNote`, `Alignment`, `Chord`, `parse_grid`.
- Produces (clés et valeurs identiques au dict `R` du prototype) :
  - `pitch.pitch_metrics(notes, beat_chords) -> dict` : `pitch_classes_pct`, `key`, `minor_penta_pct`,
    `per_chord`, `held_4th_on_dominant`, `register`, `per_chorus`.
  - `arrivals.arrival_metrics(notes, bars, beats_per_bar) -> dict` : `arrivals`, `arrival_functions`.
  - `rhythm.rhythm_metrics(notes, period_s, beats_per_bar) -> dict` : `timing`, `silences`.
  - `motifs.motif_metrics(notes) -> dict` : `top_motifs`.
  - `metrics.compute(notes, al, beat_chords, bars, beats_per_bar) -> dict` : fusion dans l'ordre du prototype.
  - `notes` vide → `DetectionError("aucune note détectée sur la piste guitare")`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_penta_only_solo(al, bc, bars):  # C Eb F G Bb, une note par temps, mesures 1-4 (C7)
    notes = [Note(1.0 + 0.5 * i, 0.4, [60, 63, 65, 67, 70][i % 5], -10) for i in range(16)]
    m = compute(place_notes(notes, al, bc, 4), al, bc, bars, 4)
    assert m["minor_penta_pct"] == 100.0 and m["key"] == "C"
    assert m["per_chord"]["C7"]["third_count"] == 0

def test_arrival_is_first_note_near_downbeat(al, bc, bars):
    notes = [Note(1.0, 0.4, 64, -10), Note(1.5, 0.4, 67, -10)]   # E au temps 1 de la mesure 1
    m = compute(place_notes(notes, al, bc, 4), al, bc, bars, 4)
    assert m["arrivals"][0]["bars"][0] == "E(3)"

def test_empty_raises():
    with pytest.raises(DetectionError):
        compute([], al, bc, bars, 4)

@pytest.mark.golden
def test_matches_prototype(example_mkv):
    ref = json.load(open("examples/MySong_20261027_183119_prototype.json"))
    m = run_pipeline(example_mkv)                  # helper de test : audio → timing → notes → form → compute
    assert m == ref["results"]
```

  Fixtures `al` (l'`Alignment` du test de Task 7), `bc` et `bars` (`parse_grid(C_JAM_BLUES, 4)`)
  dans `tests/conftest.py`.
- [ ] **Step 2:** `uv run pytest tests/test_metrics.py -v` → FAIL.
- [ ] **Step 3:** Découper `analyse()` du prototype dans les quatre modules, sans changer un calcul.
- [ ] **Step 4:** `uv run pytest tests/test_metrics.py -v -m "golden or not golden"` → PASS
  (le golden prend ~1 min).
- [ ] **Step 5:** Commit `feat: métriques migrées du prototype`.

### Task 9: `Result` et JSON versionné

**Files:**
- Create: `src/grillepain/result.py`, `src/grillepain/schema/result.schema.json`, `tests/test_result.py`

**Interfaces:**
- Consumes: `Tracks`, `Alignment`, `PlacedNote`, dict de `metrics.compute`.
- Produces:
  - `SCHEMA_VERSION = "1.0.0"`
  - `@dataclass Result: input: dict, tune: dict, alignment: Alignment, metrics: dict, notes: list[PlacedNote], warnings: list[str]`
  - `Result.to_dict() -> dict` avec exactement les clés de premier niveau :
    `schema_version`, `tool` (`{"name": "grillepain", "version": __version__}`),
    `input` (`file`, `guitar_track`, `backing_track`), `tune` (`name: null`, `grid`, `meter` ex. `"4/4"`, `bars`),
    `alignment` (`bpm`, `downbeat_s`, `method`, `confidence`, `reliable`),
    `accuracy` (`{"pitch": "fiable", "timing_ms": 20}`),
    `glossary` (R, b3, 3, 5, b7, 7, guide tone, arrivée, offbeat_phase — une phrase chacun, en français),
    `metrics`, `notes` (`PlacedNote.to_dict()`, champs `t_s`, `dur_s`, …), `warnings`.
  - `Result.write_json(path: Path)` (UTF-8, `ensure_ascii=False`, indent 1).
  - Si `not alignment.reliable` : `warnings` contient
    `"Calage du temps 1 peu fiable : les arrivées peuvent être décalées. Vérifier ou relancer avec --downbeat."`
  - `result.schema.json` : JSON Schema draft 2020-12, toutes les clés de premier niveau requises,
    `schema_version` en `const`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_schema_valid(sample_result):
    d = sample_result.to_dict()
    jsonschema.validate(d, json.load(open(SCHEMA_PATH)))
    assert d["schema_version"] == "1.0.0" and d["accuracy"]["timing_ms"] == 20

def test_unreliable_warns(sample_result_faible):
    assert sample_result_faible.to_dict()["alignment"]["reliable"] is False
    assert any("peu fiable" in w for w in sample_result_faible.warnings)
```

  `sample_result` : fixture dans `tests/conftest.py`, construite avec les objets des Tasks 5-8
  sur des données synthétiques placées à la main (pas d'audio).
- [ ] **Step 2:** `uv run pytest tests/test_result.py -v` → FAIL.
- [ ] **Step 3:** Implémenter `result.py` et le schéma ; déclarer le schéma en package data.
- [ ] **Step 4:** `uv run pytest tests/test_result.py -v` → PASS.
- [ ] **Step 5:** Commit `feat: Result et JSON à schéma versionné 1.0.0`.

### Task 10: Rapport Markdown

**Files:**
- Create: `src/grillepain/report/__init__.py`, `src/grillepain/report/markdown.py`, `tests/test_markdown.py`

**Interfaces:**
- Consumes: `Result`.
- Produces: `report.markdown.render(r: Result) -> str` — même texte que `report_md` du prototype ;
  seul ajout : si `r.warnings` non vide, une ligne `**Attention :** <warning>` par avertissement,
  juste après la liste d'en-tête.

- [ ] **Step 1: Tests qui échouent**

```python
def test_warning_line(sample_result_faible):
    assert "**Attention :** Calage du temps 1 peu fiable" in render(sample_result_faible)

@pytest.mark.golden
def test_identical_to_prototype(example_mkv):
    md = render(run_result(example_mkv))           # helper : pipeline complet → Result
    ref = open("examples/MySong_20261027_183119_analyse.md").read()
    strip = lambda s: "\n".join(l for l in s.splitlines() if not l.startswith("**Attention :**"))
    assert strip(md) == strip(ref)
```

- [ ] **Step 2:** `uv run pytest tests/test_markdown.py -v -m "golden or not golden"` → FAIL.
- [ ] **Step 3:** Porter `report_md` en lisant `Result`.
- [ ] **Step 4:** Même commande → PASS.
- [ ] **Step 5:** Commit `feat: rapport Markdown`.

### Task 11: Commande `grillepain analyse` et codes retour

**Files:**
- Modify: `src/grillepain/cli.py`
- Create: `src/grillepain/pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: tout ce qui précède.
- Produces:
  - `pipeline.run(tracks: Tracks, grid: str, beats_per_bar: int, bpm: float | None, downbeat: float | None, min_db: float, file_name: str) -> Result`
    (les helpers de test `run_pipeline` / `run_result` des Tasks 8 et 10 l'utilisent).
  - `grillepain analyse [MKV] [--guitar F --backing F] [--grid G] [--beats-per-bar N] [--bpm X]
    [--downbeat S] [--min-db D] [-o PREFIX] [--quiet]` : écrit `PREFIX_analyse.md` et `PREFIX_analyse.json`
    (défaut : à côté de l'entrée), affiche le Markdown sauf `--quiet`, progression sur stderr.
  - `main()` retourne 0 / 3 (calage peu fiable) ; attrape `GrillepainError` → message
    `grillepain : <message>` sur stderr et `exit_code`. Aucun traceback pour ces erreurs.
  - Point d'entrée : `sys.exit(main())` dans `__main__.py` et le script.

- [ ] **Step 1: Tests qui échouent** (mkv synthétiques via `tests/synth.py` ; ~10 s de musique)

```python
def test_end_to_end(tmp_path):
    p = tmp_path / "ma prise é.mkv"
    make_take(p, count_in=True)                      # helper : backing C Jam Blues 120 bpm + mélodie
    assert main(["analyse", str(p), "--quiet"]) == 0
    d = json.load(open(tmp_path / "ma prise é_analyse.json"))
    assert d["schema_version"] == "1.0.0" and d["alignment"]["reliable"] is True

def test_silent_guitar_exit_5(tmp_path, capsys):
    p = tmp_path / "x.mkv"; make_take(p, count_in=True, guitar_silent=True)
    assert main(["analyse", str(p), "--quiet"]) == 5
    assert "aucune note" in capsys.readouterr().err

def test_missing_file_exit_4(tmp_path):
    assert main(["analyse", str(tmp_path / "absent.mkv")]) == 4

def test_bad_grid_exit_2(tmp_path):
    p = tmp_path / "x.mkv"; make_take(p, count_in=True)
    assert main(["analyse", str(p), "--grid", "C7|H7"]) == 2

def test_low_confidence_exit_3(tmp_path, monkeypatch):
    p = tmp_path / "x.mkv"; make_take(p, count_in=True)
    real_align = pipeline.align
    monkeypatch.setattr(pipeline, "align",
                        lambda *a, **k: dataclasses.replace(real_align(*a, **k), confidence="faible"))
    assert main(["analyse", str(p), "--quiet"]) == 3
```

- [ ] **Step 2:** `uv run pytest tests/test_cli.py -v` → FAIL.
- [ ] **Step 3:** Implémenter `pipeline.run` (qui importe `align` au niveau module :
  `from grillepain.timing import align`) et la sous-commande.
- [ ] **Step 4:** `uv run pytest -v` → PASS (tous les tests non golden).
- [ ] **Step 5:** Commit `feat: commande grillepain analyse et codes retour`.

### Task 12: Bascule et nettoyage

**Files:**
- Delete: `solo_analyzer.py` (l'historique git le garde)
- Modify: `README.md`

- [ ] **Step 1:** `uv run pytest -v -m "golden or not golden"` → tout PASS, golden compris.
- [ ] **Step 2:** `uv run grillepain analyse examples/MySong_20261027_183119.mkv -o /tmp/g` ;
  `echo $?` → 3 (la prise d'exemple a une confiance faible) ; `/tmp/g_analyse.md` contient la
  ligne `**Attention :**`.
- [ ] **Step 3:** Supprimer `solo_analyzer.py` ; README : installation (`uv tool install .`),
  usage `grillepain analyse prise.mkv`, tableau des codes retour, lien vers le schéma JSON.
- [ ] **Step 4:** Commit `chore: bascule du prototype vers le package grillepain`.
