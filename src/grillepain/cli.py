"""Ligne de commande grillepain."""
import argparse

from grillepain import __version__


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="grillepain", description="Analyse de solos de guitare JamCapture")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="commande")
    sub.add_parser("analyse", help="analyser un enregistrement")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.commande is None:
        ap.print_help()
    return 0
