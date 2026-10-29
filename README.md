# grillepain

> « Il te grille si tu sors de la grille. »

Analyseur de solos de guitare jazz/blues enregistrés avec [JamCapture](https://github.com/AudioLibreLab/JamCapture) :
notes jouées par accord, guide tones, notes d'arrivée, mise en place, et surtout
« est-ce que je sens la grille ? ». Voir `info.md` pour les objectifs.

## Installation

Prérequis : [ffmpeg](https://ffmpeg.org/) et [uv](https://docs.astral.sh/uv/).

```sh
uv tool install .
```

## Usage

```sh
grillepain analyse prise.mkv
grillepain analyse prise.mkv --grid "C7|F7|C7|C7|F7|F7|C7|A7|Dm7|G7|C7 A7|Dm7 G7" --bpm 115
```

Options principales :

- `--grid` : grille d'accords, mesures séparées par `|`
- `--bpm` : tempo approximatif, qui aide la détection (il n'est pas imposé ; sinon détecté)
- `--downbeat` : temps 1 du 1er chorus, en secondes (sinon détecté)
- `-o` : préfixe des fichiers de sortie (`<préfixe>_analyse.json`, `<préfixe>_analyse.md`)
- `--quiet` : ne pas afficher le Markdown sur la sortie standard
- `--guitar` / `--backing` : deux fichiers audio séparés (guitare, accompagnement), utilisés uniquement sans .mkv

Exemple de rapport : `examples/MySong_20261027_183119_analyse.md`.

## Codes de retour

| Code | Signification |
|------|---------------|
| 0 | OK, calage fiable |
| 3 | OK, calage peu fiable (relancer avec `--downbeat`) |
| 2 | erreur d'usage |
| 4 | fichier illisible / pistes introuvables |
| 5 | tempo ou notes non détectés |

## Format JSON

Schéma : `src/grillepain/schema/result.schema.json` (`schema_version` 1.0.0).

## Développement

```sh
uv run pytest
uv run pytest -m golden
```

Les tests `golden` ont besoin de `examples/MySong_20261027_183119.mkv` (non versionné).
