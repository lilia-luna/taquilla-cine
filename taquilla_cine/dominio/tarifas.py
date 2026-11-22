"""Tarifas por tipo de persona.

Patrón Strategy: cada tarifa encapsula su descuento y sus restricciones; el
resto del sistema solo llama a ``precio`` y ``validar`` sin preguntar de qué
tarifa se trata (polimorfismo).
"""

import unicodedata
from abc import ABC, abstractmethod
from decimal import Decimal

from ..excepciones import TarifaNoPermitidaError
from ..utilidades import nombre_dia


class Tarifa(ABC):
    """Tarifa abstracta: descuento sobre el precio base más reglas de uso."""

    nombre = "abstracta"

    @property
    @abstractmethod
    def porcentaje_descuento(self) -> Decimal:
        """Porcentaje de descuento (0 a 100)."""

    def precio(self, precio_base: Decimal) -> Decimal:
        """Precio final después de aplicar el descuento."""
        factor = (Decimal(100) - self.porcentaje_descuento) / Decimal(100)
        return (Decimal(precio_base) * factor).quantize(Decimal("0.01"))

    def validar(self, funcion) -> None:
        """Lanza TarifaNoPermitidaError si la tarifa no puede usarse en la función.

        Por omisión una tarifa se puede usar en cualquier función.
        """

    def __str__(self) -> str:
        return self.nombre


class TarifaGeneral(Tarifa):
    """Sin descuento."""

    nombre = "general"

    @property
    def porcentaje_descuento(self) -> Decimal:
        return Decimal(0)


class TarifaEstudiante(Tarifa):
    """30 % de descuento, solo para funciones de lunes a viernes."""

    nombre = "estudiante"

    @property
    def porcentaje_descuento(self) -> Decimal:
        return Decimal(30)

    def validar(self, funcion) -> None:
        if funcion.inicio.weekday() >= 5:
            raise TarifaNoPermitidaError(
                "la tarifa estudiante solo aplica de lunes a viernes "
                f"(la función {funcion.id} es en {nombre_dia(funcion.inicio.date())})"
            )


class TarifaAdultoMayor(Tarifa):
    """50 % de descuento."""

    nombre = "adulto_mayor"

    @property
    def porcentaje_descuento(self) -> Decimal:
        return Decimal(50)


class TarifaNino(Tarifa):
    """40 % de descuento; no aplica en salas VIP ni en películas clasificación C."""

    nombre = "nino"

    @property
    def porcentaje_descuento(self) -> Decimal:
        return Decimal(40)

    def validar(self, funcion) -> None:
        if funcion.sala.tipo == "VIP":
            raise TarifaNoPermitidaError("no se venden boletos de niño para salas VIP")
        if funcion.pelicula.clasificacion == "C":
            raise TarifaNoPermitidaError("no se venden boletos de niño para películas clasificación C")


_TARIFAS = {t.nombre: t for t in (TarifaGeneral(), TarifaEstudiante(), TarifaAdultoMayor(), TarifaNino())}


def _normalizar(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", texto.strip().lower()) if not unicodedata.combining(c)
    )
    return sin_acentos.replace(" ", "_").replace("-", "_")


def nombres_de_tarifas() -> list:
    """Nombres válidos de tarifa."""
    return list(_TARIFAS)


def tarifas_disponibles() -> list:
    """Todas las tarifas del cine."""
    return list(_TARIFAS.values())


def obtener_tarifa(nombre: str) -> Tarifa:
    """Fábrica: devuelve la tarifa por nombre (acepta 'niño', 'Adulto Mayor'...)."""
    tarifa = _TARIFAS.get(_normalizar(nombre or ""))
    if tarifa is None:
        raise TarifaNoPermitidaError(
            f"la tarifa '{nombre}' no existe (use: {', '.join(nombres_de_tarifas())})"
        )
    return tarifa
