"""Aides de test : chaîne complète sur un .mkv et prises synthétiques."""
import json
from pathlib import Path

import synth
from grillepain import pipeline
from grillepain.audio import load_mkv
from grillepain.result import Result
from grillepain.theory import C_JAM_BLUES


def run_result(mkv: Path, downbeat: float | None = None) -> Result:
    """Chaîne complète avec les défauts du prototype (sans --bpm ; --downbeat optionnel)."""
    return pipeline.run(load_mkv(mkv), C_JAM_BLUES, 4, None, downbeat, -40, Path(mkv).name)


def run_pipeline(mkv: Path, downbeat: float | None = None) -> dict:
    """Chaîne complète -> métriques en dict JSON."""
    return json.loads(json.dumps(run_result(mkv, downbeat).metrics, default=float))


def make_take(path: Path, count_in: bool = True, guitar_silent: bool = False) -> None:
    """Prise synthétique : C Jam Blues à 120 bpm (1 chorus dès 2 s) + quelques notes de guitare."""
    backing = synth.chord_backing(C_JAM_BLUES, 120, 4, start_s=2.0, choruses=1, count_in=count_in)
    dur = len(backing) / synth.SR
    if guitar_silent:
        guitar = synth.silence(dur)
    else:  # (début s, durée s, midi) : pentatonique de do, dans le chorus 1
        guitar = synth.melody([(2.0, 0.4, 60), (3.0, 0.4, 63), (4.0, 0.4, 65), (5.0, 0.4, 67),
                               (6.0, 0.4, 70), (8.0, 0.4, 60)], dur)
    synth.make_mkv(path, guitar, backing)
