Projet : grillepain — analyseur de solos de guitare jazz/blues.
"Il te grille si tu sors de la grille."

CONTEXTE
Je suis guitariste (15 ans, funk/soul/blues, ~1 an de jazz). Deux problèmes :
1. Je "surfe" sur une gamme (penta mineure surtout) au lieu de suivre les accords.
2. Je perds la grille pendant mes solos : je ne sens pas où je suis dans la forme.
J'enregistre mes prises avec JamCapture (mon app Go, multi-pistes) : un .mkv FLAC
48 kHz avec une piste guitare (ex. "carla") et une piste backing (ex. "chrome",
iReal, YouTube).

POINT DE DÉPART
solo_analyzer.py (joint) fonctionne déjà : extraction des pistes via ffmpeg,
tempo (librosa beat_track), calage du temps 1 (décompte détecté, sinon
ajustement harmonique chroma/grille, sinon --downbeat), détection des notes
(pyin + onsets), puis métriques : % penta mineure, notes par accord, guide
tones, tierces, notes d'arrivée au temps 1, 4te tenue sur dominante, mise en
place (décalage ms, ratio swing), silences, registre, motifs répétés.
Sortie : rapport Markdown + JSON.

OBJECTIFS
1. Package Python propre (uv), CLI `grillepain`, tests pytest avec audio
   synthétique (notes et clics générés).
2. Grilles en YAML par standard (C Jam Blues, Autumn Leaves, Blue Bossa…) :
   intro, nombre de chorus, 3/4, accords sur 2 temps.
3. Calage du temps 1 robuste : décompte prioritaire, score de confiance
   explicite, et commande `grillepain check` qui exporte un WAV avec un clic
   au temps 1 sur le backing pour vérifier à l'oreille.
4. "Sentir la grille" — métriques dédiées :
   - est-ce que mes phrases respectent la forme (départs/fins aux mesures
     1, 5, 9 ; question/réponse sur 4 mesures) ;
   - est-ce que je marque les changements d'accord (notes qui changent
     quand l'accord change vs mêmes notes partout) ;
   - est-ce que je joue le turnaround (mesures 11-12) ou si je le traverse.
5. Suivi de progression : historique des prises (SQLite) et comparaison
   prise N vs N-1 sur les métriques clés.
6. Rapport HTML : grille colorée mesure × chorus, note d'arrivée colorée
   selon sa fonction (tierce/7e = vert, fondamentale/5te = neutre,
   hors accord = orange), phrases dessinées sur la forme.
7. Intégration JamCapture : `grillepain analyse prise.mkv --tune c-jam-blues`
   appelable en fin de prise, code retour propre, JSON à schéma versionné
   lisible par l'app Go.

CONTRAINTES
- Linux, Python 3.11+, librosa, pas de GPU.
- Honnête sur la précision : hauteurs fiables, timing ±20 ms ; le rapport
  le dit, et signale quand le calage du temps 1 est peu fiable.
- Rapport en français, concis, avec en fin "3 choses à travailler à la
  prochaine prise".

Commence par me proposer l'architecture et le plan, puis on avance étape par étape.
