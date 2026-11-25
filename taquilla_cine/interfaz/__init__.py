"""Interfaz de usuario en terminal: comandos (argparse) y menú de texto."""

from .aplicacion import Aplicacion
from .cli import ejecutar

__all__ = ["Aplicacion", "ejecutar"]
