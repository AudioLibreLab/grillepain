"""Résultat unique de l'analyse et son JSON versionné (contrat lu par JamCapture)."""
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .form import PlacedNote
from .timing import Alignment

SCHEMA_VERSION = "1.0.0"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "result.schema.json"

WARN_UNRELIABLE = ("Calage du temps 1 peu fiable : les arrivées peuvent être décalées. "
                   "Vérifier ou relancer avec --downbeat.")

GLOSSARY = {
    "R": "Fondamentale de l'accord en cours.",
    "b3": "Tierce mineure de l'accord en cours.",
    "3": "Tierce majeure de l'accord en cours.",
    "5": "Quinte juste de l'accord en cours.",
    "b7": "Septième mineure (de dominante) de l'accord en cours.",
    "7": "Septième majeure de l'accord en cours.",
    "guide tone": "Tierce ou septième de l'accord : les notes qui définissent sa couleur harmonique.",
    "arrivée": "Première note jouée près du temps 1 d'une mesure, avec sa fonction dans l'accord.",
    "offbeat_phase": "Position moyenne des notes par rapport au temps, en fraction de temps ; "
                     "révèle une avance ou un retard systématique.",
}


@dataclass
class Result:
    input: dict
    tune: dict
    alignment: Alignment
    metrics: dict
    notes: list[PlacedNote]
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.alignment.reliable and WARN_UNRELIABLE not in self.warnings:
            self.warnings.append(WARN_UNRELIABLE)

    def to_dict(self) -> dict:
        a = self.alignment
        return {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": "grillepain", "version": __version__},
            "input": self.input,
            "tune": self.tune,
            "alignment": {"bpm": float(a.bpm), "downbeat_s": float(a.downbeat_s),
                          "method": a.method, "method_id": a.method_id,
                          "confidence": a.confidence,
                          "reliable": bool(a.reliable)},
            "accuracy": {"pitch": "fiable", "timing_ms": 20},
            "glossary": dict(GLOSSARY),
            "metrics": self.metrics,
            "notes": [n.to_dict() for n in self.notes],
            "warnings": self.warnings,
        }

    def write_json(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1),
                              encoding="utf-8")
