# grillepain — design

> « Il te grille si tu sors de la grille. »

Date : 2026-10-28 · Point de départ : `solo_analyzer.py` (prototype fonctionnel) et `info.md`.

## 1. But

Aider un guitariste (funk/soul/blues, ~1 an de jazz) à corriger deux défauts :

1. **Surfer sur une gamme** (penta mineure) au lieu de suivre les accords.
2. **Perdre la grille** pendant le solo.

grillepain analyse une prise JamCapture (`.mkv`, une piste guitare + une piste backing) et
produit un rapport court en français qui finit par « 3 choses à travailler à la prochaine prise ».

**Critères de succès**

- Une commande, appelable par JamCapture en fin de prise :
  `grillepain analyse prise.mkv --tune c-jam-blues`.
- Le calage du temps 1 est soit fiable, soit **signalé comme douteux**, et vérifiable à
  l'oreille en 10 secondes (`grillepain check`).
- Les métriques « sentir la grille » distinguent une prise qui suit la forme d'une prise qui
  la traverse (validé sur audio synthétique et sur les vraies prises).
- La progression se suit d'une prise à l'autre.
- Le JSON produit est assez explicite pour qu'une IA (Claude ou autre) puisse commenter la
  prise sans autre contexte.

**Hors périmètre** : transcription complète (pas de partition), GPU / modèles neuronaux,
temps réel, autres instruments que la guitare.

## 2. Contraintes

- Linux, Python ≥ 3.11, `uv`, librosa, ffmpeg. Pas de GPU.
- Honnêteté sur la précision : hauteurs fiables, timing ±20 ms ; le rapport le dit et
  signale un calage peu fiable.
- Rapport en français, concis.
- Les prises audio ne sont pas versionnées (`.gitignore`) ; les tests utilisent de l'audio
  synthétique.

## 3. Architecture

```
src/grillepain/
  cli.py          analyse | check | eval | history | tunes
  audio.py        ffprobe/ffmpeg : extraction et choix des pistes (titre, index)
  theory.py       Chord, qualités, fonction d'une note dans un accord
  tunes.py        chargement/validation des grilles YAML
  tunes/*.yaml    une grille par standard
  timing.py       tempo, temps, décompte, ajustement harmonique → Alignment(+confiance)
  notes.py        pyin + onsets → list[Note]
  form.py         place chaque note : chorus, mesure, temps, accord, fonction
  metrics/
    pitch.py      % penta, répartition, registre, notes par accord, guide tones, tierces
    arrivals.py   notes d'arrivée au temps 1, 4te tenue sur dominante
    form.py       « sentir la grille » (§6)
    rhythm.py     décalage, dispersion, ratio swing, silences
    motifs.py     motifs répétés
  advice.py       sélection des « 3 choses à travailler »
  result.py       dataclasses Result + sérialisation JSON (schéma versionné)
  report/
    markdown.py
    html.py
  history.py      SQLite
tests/
  synth.py        générateurs : clics, notes sinusoïdales/pincées, backing d'accords
```

Chaque module a une entrée et une sortie typées ; seuls `audio.py` et `cli.py` touchent au
système de fichiers et à ffmpeg.

### Flux

```
prise.mkv ─audio→ (guitare, backing)
backing ─timing→ Alignment {bpm, beats[], downbeat_t, méthode, confiance}
guitare ─notes→  Note[] {t, dur, midi, level_db}
Alignment + Tune + Note[] ─form→ PlacedNote[] {chorus, bar, beat, chord, function}
PlacedNote[] ─metrics→ Metrics
→ Result {schema_version, meta, alignment, tune, notes, metrics, advice, warnings}
Result → JSON · Markdown · HTML · SQLite
```

`Result` est la seule source des rendus : rien n'est recalculé dans les rapports.

## 4. Grilles (YAML)

```yaml
# tunes/c-jam-blues.yaml
name: C Jam Blues
meter: 4/4            # 3/4 accepté
intro_bars: 0         # mesures avant le 1er chorus
choruses: null        # null = autant que l'audio en contient
form:                 # une ligne = une mesure ; plusieurs accords = partage égal
  - C7
  - F7
  - C7
  - C7
  - F7
  - F7
  - C7
  - A7
  - Dm7
  - G7
  - C7 A7
  - Dm7 G7
sections:             # optionnel, pour les métriques de forme
  turnaround: [11, 12]
```

- Accords sur 2 temps : `C7 A7` dans une mesure de 4/4 → 2 temps chacun. Partage explicite
  possible : `C7:3 A7:1`.
- Grilles fournies : C Jam Blues, Autumn Leaves, Blue Bossa.
- L'utilisateur fournit la grille de trois façons :
  - `--tune <nom>` : cherché dans `~/.config/grillepain/tunes/` puis dans les grilles
    fournies (une grille perso du même nom l'emporte) ;
  - `--tune ./ma-grille.yaml` : chemin direct vers un fichier YAML ;
  - `--grid "C7|F7|…"` : grille ad hoc en ligne de commande (4/4, sans intro).
- **Import iReal Pro** : `grillepain tunes import <source>` convertit une grille iReal en
  YAML dans `~/.config/grillepain/tunes/` (à relire/corriger ensuite). Sources acceptées :
  lien `irealb://…` (partage ou export HTML d'une playlist, plusieurs morceaux possibles) et
  export MusicXML. Points délicats : déchiffrement du format `irealb` (bibliothèque
  `pyRealParser` si elle est fiable, sinon petit parseur maison testé), dépliage des
  reprises, 1re/2e fins, codas et signes de répétition de mesure, normalisation des symboles
  d'accords iReal (`-7`, `^7`, `h7`, `o7`…) vers `theory.py`. Mesure, tonalité et forme
  dépliée sont reprises telles quelles ; l'intro et `sections` restent à compléter à la main.
- Une grille invalide (accord inconnu, mesure vide, partage qui ne tombe pas juste) donne
  un message clair avec le numéro de mesure, code retour 2.
- `grillepain tunes` liste les grilles disponibles.
- `sections` par défaut pour un blues de 12 mesures : phrases 1/5/9, turnaround 11-12.
  Pour les formes AABA / 32 mesures : sections A/B et turnaround = 2 dernières mesures.

## 5. Calage du temps 1

Le temps 1 du premier chorus fixe la position de toutes les notes dans la grille ; une erreur
d'un temps fausse toute l'analyse. Méthodes, par ordre de priorité :

1. `--downbeat <s>` (manuel) : confiance « manuelle ».
2. **Décompte** détecté (clics brefs, isolés, réguliers, cohérents avec le tempo) :
   confiance haute si ≥ 3 clics réguliers.
3. **Ajustement harmonique** : chroma du backing synchronisé sur les temps, corrélé à la grille
   pour chaque décalage possible ; on garde le meilleur.

**Indice de basse** (le plus discriminant, à combiner à l'ajustement harmonique) : la basse
joue en général la fondamentale de l'accord au temps 1 de chaque mesure (walking, bossa,
blues). On isole le registre grave du backing (passe-bas ~250 Hz, chroma ou pyin grave)
au début de chaque temps, et on score chaque décalage par la part de temps 1 où la note de
basse = fondamentale de l'accord de la grille. Plus robuste que le chroma global, brouillé
par les voicings sans fondamentale du piano. Sert aussi de contrôle de la grille elle-même
(fondamentale jamais entendue sur une mesure → grille probablement fausse à cet endroit).

**Indices de batterie (cymbales)**, combinés à l'ajustement harmonique, jamais seuls (un
backing peut ne pas en avoir) :
- *Crash* : attaque forte au-dessus de ~5 kHz suivie d'une longue décroissance ; tombe
  souvent sur le temps 1 d'un début de chorus ou de section. Bonus aux décalages qui placent
  les crashs sur la mesure 1 (ou un début de section).
- *Charleston au pied / backbeat* : accents aigus courts sur les temps 2 et 4 ; tranche
  l'ambiguïté temps 1 / temps 2 (erreur de phase la plus fréquente).

**Score de confiance** (0–1, plus une étiquette haute/moyenne/faible) calculé à partir de :
la marge entre le meilleur et le 2e décalage, la stabilité du tempo, l'accord entre décompte,
ajustement harmonique, basse et cymbales quand ils existent. Le rapport l'affiche en tête ; en confiance
faible, il met un avertissement visible et propose `grillepain check`.

**`grillepain check prise.mkv`** : exporte `prise_check.wav` = backing + un clic aigu au
temps 1 de chaque mesure (clic plus marqué au début de chaque chorus). L'utilisateur écoute ;
si c'est faux, il relance avec `--downbeat` ou `--shift ±N` (décalage en temps).

Les calages validés à l'oreille sont enregistrés (`history.py`, colonne
`downbeat_verified`) et forment le **corpus de référence** de §9.

## 6. Métriques « sentir la grille »

Calculées sur `PlacedNote[]` et la segmentation en **phrases** (une phrase = notes séparées
par un silence ≥ 1 temps, seuil réglable).

1. **Respect de la forme**
   - Position du départ et de la fin de chaque phrase dans la forme ; % de phrases qui
     commencent dans la zone des mesures 1, 5, 9 (±1 temps, ou en levée dans la mesure
     précédente).
   - Longueur des phrases en mesures ; part des phrases de 2 ou 4 mesures (structure
     question/réponse).
2. **Marquer les changements d'accord**
   - Pour chaque changement d'accord, on compare les notes jouées dans le temps qui précède
     et dans celui qui suit : la note d'arrivée est-elle une note de l'accord nouveau ?
     Est-ce un guide tone qui bouge d'un demi-ton ?
   - Indice « surf » : similarité des distributions de classes de hauteur entre accords
     différents (identiques partout = surf sur la gamme).
3. **Turnaround (mesures 11-12 ou section `turnaround`)**
   - Densité de notes, % de notes de l'accord, présence de notes caractéristiques
     (ex. C# sur A7, B sur G7) vs mêmes notes que le reste du chorus.
   - Verdict par chorus : « joué » / « traversé » / « silence ».

Chaque métrique a un test synthétique qui la fait passer de bonne à mauvaise.

## 7. Sorties

### JSON (contrat avec JamCapture et brief IA)

- `schema_version` (semver, commence à `1.0.0`) ; schéma JSON publié dans
  `src/grillepain/schema/result.schema.json`.
- Autodescriptif : unités dans les noms de champs (`t_s`, `offset_ms`), `glossary` court
  (R, b7, guide tone…), précision annoncée (`accuracy: {pitch, timing_ms}`), confiance du
  calage, `warnings[]`.
- Contient la grille, par chorus × mesure les notes avec leur fonction, les phrases, les
  métriques et les 3 conseils. Pas de fichier « brief IA » séparé : le JSON en tient lieu.

### Codes retour

| Code | Sens |
|---|---|
| 0 | analyse produite, calage fiable |
| 3 | analyse produite, calage peu fiable (avertissement) |
| 2 | erreur d'usage (grille inconnue, option invalide) |
| 4 | fichier illisible / pistes introuvables |
| 5 | tempo ou notes non détectés |

### Markdown

Le rapport actuel, réorganisé : en-tête (grille, tempo, calage + confiance), « Sentir la
grille », notes par accord, arrivées, mise en place, motifs, précision, puis
**3 choses à travailler** et, s'il y a un historique, l'**évolution vs prise précédente**.

### HTML

Fichier autonome (pas de CDN obligatoire) :
- grille mesure × chorus, chaque case colorée par la fonction de la note d'arrivée
  (tierce/7e = vert, fondamentale/5te = neutre, hors accord = orange) ;
- phrases dessinées comme des barres sur la forme ;
- mêmes blocs de texte que le Markdown.

### 3 choses à travailler

`advice.py` choisit 3 conseils dans une liste de règles (seuil sur une métrique → conseil
concret et exercice), triées par écart à l'objectif. Exemple : guide tones < 20 % →
« viser la 3ce ou la 7e au temps 1 de chaque mesure ». Pas de génération libre.

## 8. Historique (SQLite)

- Base : `~/.local/share/grillepain/history.sqlite`.
- Table `takes` (fichier, hash, date, tune, bpm, calage, confiance, `downbeat_verified`,
  JSON complet) + table `metrics` (take_id, clé, valeur) pour comparer facilement.
- `grillepain history [--tune X]` : liste des prises et évolution des métriques clés.
- Le rapport compare la prise N à la prise N-1 du même morceau.

## 9. Boucle d'évaluation et d'amélioration

- **Tests pytest** sur audio synthétique : vérité connue (notes, temps 1, swing, phrases).
  Exemples : décompte + backing d'accords → temps 1 exact à ±20 ms ; solo ne jouant que la
  penta → indice « surf » élevé ; solo jouant les guide tones → faible.
- **`grillepain eval <dossier>`** : analyse toutes les prises (ex.
  `~/Audio/JamCapture/Recordings/`) et produit un tableau de cohérence (tempo stable ?,
  confiance du calage, accord décompte/harmonie, part de notes hors accord, cohérence entre
  prises d'un même morceau, écart au corpus de référence vérifié à l'oreille).
- Claude lance `eval`, lit les JSON, propose et teste des corrections, puis compare avant et
  après. L'oreille de l'utilisateur (`check`) reste la référence pour le calage.

## 10. Étapes

1. Squelette `uv` + migration du prototype vers les modules, **sans changement de
   comportement** (rapport identique sur la prise d'exemple) + premiers tests synthétiques.
2. `Result` + JSON versionné + codes retour (branchement JamCapture possible).
3. Grilles YAML (3 standards) + `grillepain tunes`.
   Puis import iReal Pro (`grillepain tunes import`).
4. **Boucle d'amélioration** : `grillepain eval` sur les vraies prises.
5. Calage robuste : indices de basse et de cymbales, score de confiance, `grillepain check`, `--shift`.
6. Métriques « sentir la grille » + `advice.py`.
7. Historique SQLite + comparaison N / N-1.
8. Rapport HTML.

Chaque étape = une session courte, livrée avec tests verts et un commit.
