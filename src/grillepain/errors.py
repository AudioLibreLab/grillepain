"""Erreurs typées ; exit_code est utilisé par la CLI."""


class GrillepainError(Exception):
    exit_code = 1


class UsageError(GrillepainError):
    """Erreur d'usage (grille, accord, options)."""
    exit_code = 2


class InputError(GrillepainError):
    """Fichier illisible ou pistes introuvables."""
    exit_code = 4


class DetectionError(GrillepainError):
    """Tempo ou notes non détectés."""
    exit_code = 5
