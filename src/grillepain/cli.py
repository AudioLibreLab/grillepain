"""Ligne de commande grillepain."""
import argparse
import sys
from pathlib import Path

from grillepain import __version__, pipeline
from grillepain.audio import load_mkv, load_pair
from grillepain.errors import GrillepainError
from grillepain.report import markdown
from grillepain.theory import C_JAM_BLUES

EXIT_UNRELIABLE = 3  # calage peu fiable : résultats écrits mais à vérifier


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="grillepain", description="Analyse de solos de guitare JamCapture")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="commande")
    an = sub.add_parser("analyse", help="analyser un enregistrement")
    an.add_argument("mkv", nargs="?", help="fichier .mkv JamCapture")
    an.add_argument("--guitar", help="piste guitare (si pas de mkv)")
    an.add_argument("--backing", help="piste backing (si pas de mkv)")
    an.add_argument("--grid", default=C_JAM_BLUES, help="grille, mesures séparées par | (défaut : C Jam Blues)")
    an.add_argument("--beats-per-bar", type=int, default=4)
    an.add_argument("--bpm", type=float, help="tempo approximatif (aide la détection)")
    an.add_argument("--downbeat", type=float, help="temps 1 du premier chorus, en secondes (prioritaire)")
    an.add_argument("--min-db", type=float, default=-40, help="seuil de niveau des notes guitare (dB / crête)")
    an.add_argument("-o", "--out", help="préfixe des fichiers de sortie (défaut : à côté de l'entrée)")
    an.add_argument("--quiet", action="store_true", help="ne pas afficher le Markdown sur stdout")
    return ap


def _analyse(ap: argparse.ArgumentParser, a: argparse.Namespace) -> int:
    if not a.mkv and not (a.guitar and a.backing):
        ap.error("donner un .mkv, ou --guitar et --backing")
    print("Chargement…", file=sys.stderr)
    if a.mkv:
        tracks, src = load_mkv(a.mkv), a.mkv
    else:
        tracks, src = load_pair(a.guitar, a.backing), a.guitar
    result = pipeline.run(tracks, a.grid, a.beats_per_bar, a.bpm, a.downbeat, a.min_db, Path(src).name)
    prefix = a.out or str(Path(src).with_suffix(""))
    md = markdown.render(result)
    Path(prefix + "_analyse.md").write_text(md, encoding="utf-8")
    result.write_json(Path(prefix + "_analyse.json"))
    if not a.quiet:
        print(md)
    print(f"→ {prefix}_analyse.md / .json", file=sys.stderr)
    return 0 if result.alignment.reliable else EXIT_UNRELIABLE


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.commande is None:
        ap.print_help()
        return 0
    try:
        return _analyse(ap, args)
    except GrillepainError as e:
        print(f"grillepain : {e}", file=sys.stderr)
        return e.exit_code
