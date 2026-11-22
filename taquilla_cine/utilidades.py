"""Funciones auxiliares de fechas, horas y dinero."""

import re
from datetime import date, datetime
from decimal import Decimal

from .excepciones import DatoInvalidoError

DIAS_SEMANA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

_PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PATRON_HORA = re.compile(r"^\d{2}:\d{2}$")


def nombre_dia(fecha: date) -> str:
    """Devuelve el nombre del día de la semana en español."""
    return DIAS_SEMANA[fecha.weekday()]


def parsear_fecha(texto: str) -> date:
    """Convierte ``AAAA-MM-DD`` en ``date``; lanza DatoInvalidoError si es inválida."""
    texto = (texto or "").strip()
    if not _PATRON_FECHA.match(texto):
        raise DatoInvalidoError(
            f"fecha inválida '{texto}' (formato esperado AAAA-MM-DD, por ejemplo 2026-11-27)"
        )
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise DatoInvalidoError(f"fecha inválida '{texto}' (esa fecha no existe en el calendario)")


def parsear_hora(texto: str):
    """Convierte ``HH:MM`` en ``time``; lanza DatoInvalidoError si es inválida."""
    texto = (texto or "").strip()
    if not _PATRON_HORA.match(texto):
        raise DatoInvalidoError(f"hora inválida '{texto}' (formato esperado HH:MM, por ejemplo 18:30)")
    try:
        return datetime.strptime(texto, "%H:%M").time()
    except ValueError:
        raise DatoInvalidoError(f"hora inválida '{texto}' (la hora debe estar entre 00:00 y 23:59)")


def parsear_fecha_hora(texto: str) -> datetime:
    """Convierte ``AAAA-MM-DD HH:MM`` (o con ``T``) en ``datetime``."""
    partes = (texto or "").strip().replace("T", " ").split()
    if len(partes) != 2:
        raise DatoInvalidoError(
            f"fecha y hora inválidas '{texto}' (formato esperado 'AAAA-MM-DD HH:MM')"
        )
    return datetime.combine(parsear_fecha(partes[0]), parsear_hora(partes[1]))


def dinero(valor: Decimal) -> str:
    """Formatea una cantidad como pesos, por ejemplo ``$1,280.00``."""
    return f"${Decimal(valor):,.2f}"
