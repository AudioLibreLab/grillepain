# Backlog grillepain

Idées hors des étapes de la spec (`docs/superpowers/specs/2026-10-28-grillepain-design.md`, §10).
À brainstormer avant tout code.

## Scores et note globale (idée du 2026-10-29)

Donner un score par axe et une note globale à chaque prise, pour une appli plus ludique.

- Axes possibles :
  - **harmonie** : notes de l'accord, guide tones, arrivées sur la 3ce ou la 7e ; malus pour la 4te tenue sur une dominante ;
  - **mise en place** : voir ci-dessous ;
  - **phrasé** : silences, variété des motifs, registre.
- Historique des prises et progression (lien avec l'étape 7, historique SQLite), défis
  (« vise la 3ce sur chaque temps 1 »), lien avec `advice.py` (étape 6).
- Point délicat : un barème musicalement juste. Un blues en penta mineure est un choix, pas
  une faute ; le barème pourrait dépendre du style ou d'un objectif choisi.

## Évaluer la précision rythmique (idée du 2026-10-29)

Le rapport actuel donne le décalage moyen sur les temps, une dispersion et la phase médiane des
croches. Il faut voir comment en tirer une vraie mesure de précision :

- Contre quoi mesurer : temps seuls, croches (avec le swing attendu), ou subdivision la plus
  proche ?
- Distinguer un **placement voulu** (jouer constamment derrière le temps, laid-back) d'une
  **imprécision** (dispersion) : la régularité compte plus que l'écart moyen.
- Stabilité dans le temps : dérive en avance ou en retard au fil des chorus.
- Swing : écart du ratio de croches au style du morceau (iReal « Medium Swing » ≈ 0,67 ?).
- Limites de mesure : précision des onsets guitare (±20 ms annoncés) et du calage des temps
  (trames de 23 ms). À valider sur des prises synthétiques à décalage connu.
- Exemple : premier essai réel (MySong_20261029_140753.mkv) : +1,6 ms en moyenne, ±67 ms de
  dispersion, croches à 0,60.
