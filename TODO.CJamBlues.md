# TODO : enregistrer et analyser un chorus sur C Jam Blues

## Backing

- Export iReal Pro : `examples/ireal-export-c-jam-blues/` (MusicXML + audio)
- Grille iReal : `C7|C7|C7|C7|F7|F7|C7|C7|G7|G7|C7|C7` (différente de la grille par défaut de grillepain)
- 100 bpm, 4 clics de décompte, temps 1 à 2,48 s, 12 chorus
- Converti pour JamCapture : `~/Audio/JamCapture/BackingTracks/C-Jam-Blues_iReal_100bpm.flac`

## Enregistrer avec JamCapture

1. Lancer `jamcapture serve` et ouvrir l'interface web **dans Chrome** : le backing
   joué par JamCapture est capté par la voie `chrome_stereo`.
2. Choisir le profil **`carla`** (guitare via Carla + Chrome). grillepain reconnaît la
   piste « chrome » comme backing.
3. **Démarrer l'enregistrement avant de lancer le backing**, pour que les 4 clics du
   décompte soient dans la prise (c'est ce qui donne la confiance haute).
4. Couper tout autre son dans Chrome (YouTube, notifications…), sinon il se retrouve
   dans la piste backing.

## Analyser la prise

```
uv run grillepain analyse ~/Audio/JamCapture/Recordings/<prise>.mkv --grid "C7|C7|C7|C7|F7|F7|C7|C7|G7|G7|C7|C7"
```

Ne pas oublier `--grid` : la grille par défaut de grillepain n'est pas celle d'iReal.
