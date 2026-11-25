"""Datos y funciones compartidas por las pruebas."""

from datetime import datetime
from pathlib import Path

from taquilla_cine.dominio import Pelicula, crear_salas_del_cine
from taquilla_cine.servicios import Cartelera, Taquilla

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
ANTES = datetime(2026, 11, 26, 12, 0)  # un día antes del viernes 27


def cartelera_demo() -> Cartelera:
    """Cartelera pequeña: F001 trad., F002 3D, F003 clasif. C, F004 VIP, F005 sábado."""
    c = Cartelera(crear_salas_del_cine())
    c.agregar(Pelicula("Galaxia", "B", 120), 1, datetime(2026, 11, 27, 14, 0))
    c.agregar(Pelicula("Luna", "A", 95), 3, datetime(2026, 11, 27, 16, 0))
    c.agregar(Pelicula("Lago", "C", 100), 2, datetime(2026, 11, 27, 20, 0))
    c.agregar(Pelicula("Cena", "B", 110), 4, datetime(2026, 11, 27, 19, 0))
    c.agregar(Pelicula("Galaxia", "B", 120), 1, datetime(2026, 11, 28, 14, 0))
    return c


def taquilla_demo() -> Taquilla:
    """Taquilla sobre la cartelera de demostración."""
    return Taquilla(cartelera_demo())
