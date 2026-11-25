"""Punto de entrada del sistema: ``python -m taquilla_cine``."""

from .interfaz.cli import ejecutar


def main(argv=None) -> int:
    """Ejecuta el programa y devuelve el código de salida."""
    return ejecutar(argv)


if __name__ == "__main__":
    raise SystemExit(main())
