# grillepain

> « Il te grille si tu sors de la grille. »

Analyseur de solos de guitare jazz/blues enregistrés avec [JamCapture](https://github.com/AudioLibreLab/JamCapture) :
notes jouées par accord, guide tones, notes d'arrivée, mise en place, et surtout
« est-ce que je sens la grille ? ».

État : prototype (`solo_analyzer.py`), voir `info.md` pour les objectifs.

```sh
python3 solo_analyzer.py prise.mkv --grid "C7|F7|C7|C7|F7|F7|C7|A7|Dm7|G7|C7 A7|Dm7 G7"
```

Exemple de rapport : `examples/MySong_20261027_183119_analyse.md`.
