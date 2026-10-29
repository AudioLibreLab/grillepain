# Phase 1 — arbitrages et points reportés

Extrait du registre d'exécution (sous-agents) de la phase 1, conservé pour les phases suivantes.

## Arbitrages
- Ruling: helpers de test dans tests/helpers.py — T8 crée run_pipeline(mkv) chaînant audio→timing→notes→form→compute ; T10 y ajoute run_result ; T11 les réécrit pour appeler pipeline.run et y ajoute make_take — ordre des tâches impose cela — coût si faux : refactor d'un fichier de test.
- Ruling: Tracks.source = "ireal" si "ireal" dans le titre backing, "youtube" si "youtube", sinon "autre" — spec §5 (déduit du nom de piste) — coût si faux : valeur à changer, pas encore dans le JSON.
- Ruling: commentaire du test penta T8 à corriger en « mesures 1-4 » — assertions inchangées — coût nul.
- Ruling: uv installé via pipx (pipx install uv) — plan T1 step 1 demandait curl|sh, pipx déjà présent et moins intrusif — coût nul.
- Ruling: T2 test décompte modifié (start_s 2.5, tolérance 0.03) — limite de librosa (pas d'onset à la trame 0) et quantification des onsets, pas un défaut du générateur ; la précision ±20 ms du produit est vérifiée en T5 sur le calage, pas sur onset_detect — coût si faux : générateur moins précis que cru, détecté en T5.
- Ruling: T5 reste une migration à l'identique (pad=True conservé) ; test_harmonic_fit_without_count_in marqué xfail(strict=True, reason bug pad) ; correction pad=False ajoutée en Task 13 (après T12) qui régénère la référence d'exemple et documente l'écart — la non-régression de la migration reste vérifiable, et le bug est corrigé dans la phase 1 — coût si faux : une tâche de plus, rapport d'exemple modifié.
- Ruling: tolérance du temps 1 dans les tests synthétiques portée à 0.05 s — le calage accroche une grille de temps beat_track (hop 512 = 23 ms) ; l'affirmation « timing ±20 ms » de la spec vaut pour les notes, l'affinage du temps 1 relève de l'étape « calage robuste » — coût si faux : promesse de précision du calage à revoir en phase calage.
- Ruling: avertissement numba « invalid value encountered in cast » (librosa.util.abs2 via pyin sur silence, dépend de l'ordre des tests) — filtre ciblé filterwarnings dans pyproject (message + module librosa), pas de changement d'algorithme — avertissement tiers sur entrée silencieuse — coût si faux : masque un vrai NaN de librosa sur entrée non silencieuse.
- Ruling: commande de vérification de référence = `uv run pytest` (les filtres ini s'appliquent) ; -W error en ligne de commande écrase le filtre. Durcissement possible : filterwarnings = ["error", "ignore:..."] — à trancher en relecture finale — coût si faux : un avertissement nouveau passerait inaperçu.
- Ruling: T13 tolérance du test harmonique synthétique 0.05 s (cohérent avec T5) — quantification de la grille beat_track — coût si faux : idem ruling T5.
- Ruling: temps 1 négatif (-0.24 s, temps extrapolé avant le début du fichier) conservé ; --downbeat refuse < 0 → l'utilisateur ne peut pas réinjecter la valeur affichée : différé à la phase « calage robuste » (check + --shift) — hérité du prototype, pas de tâche aval qui en dépend — coût si faux : confusion utilisateur sur une prise qui commence sur le temps 1.
- Ruling: un seul passage de correctifs (final-fix-brief.md) : Important 1-3 + minors « must/cheap » 4-12 ; « can wait » laissés au registre — coût si faux : quelques minors reportés.
- Ruling: ajout de alignment.method_id (enum machine) au JSON avant de figer 1.0.0 — recommandation du relecteur, la valeur `method` est un libellé français non exploitable par Go — coût si faux : un champ de plus.
- Final fix wave: re-review clean (12/12 addressed). Parked: method_id a une valeur par défaut « harmonic » (risque latent, aucun chemin réel ne s'en sert) — Ruling: laissé tel quel, à retirer à la prochaine modification d'Alignment — coût si faux : un futur constructeur étiquette mal la méthode.

## Points mineurs reportés (« can wait » de la relecture finale)
- Task 1: minor (deferred): cli sans sous-commande retourne 0 ; version dupliquée pyproject/__init__
- Task 2: minor (deferred): _mix avec t_s négatif boucle en fin de tableau (count_in avec start_s < 4 temps) ; test décompte ne vérifie pas on[1..4] ; test_make_mkv ne vérifie pas pistes/titres ; accords en octave 3 seulement (brief : 3-4) ; melody sans release
- Task 3: minor (deferred): tests d'erreur sans match= sur le texte ; GrillepainError.exit_code=1 hors table
- Task 4: minor (deferred): backing_idx seul écrasé par l'heuristique ; pas de contrôle guitar_idx != backing_idx ; stderr ffmpeg non repris dans le message ; pas de test fichier corrompu
- Task 5: minor (deferred): beat_chords vide → ZeroDivisionError (comme le prototype) ; boucle « tenir jusqu'au changement » de synth.chord_backing peu lisible ; synth saute des accords si plus d'accords que de temps ; fixture parse_grid dupliquée
- Task 6: minor (deferred): notes.py sans annotations de type ; audio < 1 trame pyin → IndexError (comme le prototype) ; release 50 ms ajoutée à synth.melody
- Task 7: minor (deferred): __dataclass_fields__ au lieu de dataclasses.fields ; beats < 2 → IndexError (comme le prototype)
- Task 8: minor (deferred): sous-métriques sans garde sur entrée vide (seul compute garde) ; ordre des imports conftest ; ordre des clés non vérifié par le golden ; pas de tests unitaires rhythm/motifs
- Task 10: minor (deferred): pas de ligne vide entre avertissements et « ## Notes jouées » (plusieurs avertissements fusionnent en un paragraphe) ; golden ignore le \n final
- Task 12: minor (deferred): README ne dit pas que --guitar/--backing vont ensemble et sans mkv ; formulation --bpm imprécise
- Task 13: minor (deferred): chemin first>0 (temps 1 extrapolé négatif) sans test synthétique ; golden md retire encore « **Attention :** » alors que la référence le contient ; paramètre beat_frames inutilisé dans fit_form ; valeur négative affichée non réinjectable via --downbeat

Déjà corrigés dans la passe finale : grille vide / mesure ≤ 0 / bpm ≤ 0 (exit 2), OSError d'écriture (exit 4), schéma typé + method_id, README, golden md complet, fichiers fermés dans les tests, filterwarnings=error, avertissement pyin, copie de GLOSSARY, mkv exclusif avec --guitar/--backing, tests exit 3/5 renforcés, default=float retiré.
