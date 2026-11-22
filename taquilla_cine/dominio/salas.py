"""Salas del cine.

``Sala`` es una clase abstracta: cada tipo de sala decide su precio base
(polimorfismo). ``crear_sala`` es una fábrica que construye la sala correcta a
partir de su tipo.
"""

import re
from abc import ABC, abstractmethod
from decimal import Decimal
from string import ascii_uppercase

from ..excepciones import AsientoInvalidoError, DatoInvalidoError

_PATRON_ASIENTO = re.compile(r"^([A-Za-z])(\d{1,3})$")


class Sala(ABC):
    """Sala con filas (A, B, C...) y asientos numerados por fila."""

    PRECIO_TRADICIONAL = Decimal("80")
    tipo = "abstracta"

    def __init__(self, numero: int, filas: int, asientos_por_fila: int):
        if not 1 <= filas <= len(ascii_uppercase):
            raise DatoInvalidoError(f"una sala debe tener entre 1 y {len(ascii_uppercase)} filas")
        if asientos_por_fila < 1:
            raise DatoInvalidoError("una sala debe tener al menos un asiento por fila")
        self._numero = numero
        self._filas = filas
        self._asientos_por_fila = asientos_por_fila

    @property
    def numero(self) -> int:
        """Número de la sala (1 a 4 en este cine)."""
        return self._numero

    @property
    def filas(self) -> int:
        """Cantidad de filas."""
        return self._filas

    @property
    def asientos_por_fila(self) -> int:
        """Cantidad de asientos en cada fila."""
        return self._asientos_por_fila

    @property
    def capacidad(self) -> int:
        """Total de asientos de la sala."""
        return self._filas * self._asientos_por_fila

    @property
    @abstractmethod
    def precio_base(self) -> Decimal:
        """Precio del boleto con tarifa general en esta sala."""

    def etiquetas_filas(self) -> list:
        """Letras de las filas: ['A', 'B', ...]."""
        return list(ascii_uppercase[: self._filas])

    def asientos(self) -> list:
        """Todos los asientos de la sala, en orden (A1, A2, ..., B1, ...)."""
        return [f"{fila}{n}" for fila in self.etiquetas_filas() for n in range(1, self._asientos_por_fila + 1)]

    def normalizar_asiento(self, texto: str) -> str:
        """Valida un asiento escrito por el usuario y lo devuelve en mayúsculas.

        Lanza AsientoInvalidoError si el asiento no existe en esta sala.
        """
        coincidencia = _PATRON_ASIENTO.match((texto or "").strip())
        if not coincidencia:
            raise AsientoInvalidoError(f"asiento '{texto}' inválido (use fila y número, por ejemplo A1)")
        fila, numero = coincidencia.group(1).upper(), int(coincidencia.group(2))
        if fila not in self.etiquetas_filas() or not 1 <= numero <= self._asientos_por_fila:
            raise AsientoInvalidoError(
                f"el asiento {fila}{numero} no existe en la sala {self._numero} "
                f"(filas A-{self.etiquetas_filas()[-1]}, asientos 1-{self._asientos_por_fila})"
            )
        return f"{fila}{numero}"

    def __str__(self) -> str:
        return f"Sala {self._numero} ({self.tipo})"


class SalaTradicional(Sala):
    """Sala tradicional: el boleto cuesta $80."""

    tipo = "tradicional"

    @property
    def precio_base(self) -> Decimal:
        return self.PRECIO_TRADICIONAL


class Sala3D(Sala):
    """Sala 3D: precio tradicional más $30 por los lentes."""

    tipo = "3D"
    SOBRECARGO_LENTES = Decimal("30")

    @property
    def precio_base(self) -> Decimal:
        return self.PRECIO_TRADICIONAL + self.SOBRECARGO_LENTES


class SalaVIP(Sala):
    """Sala VIP: el boleto cuesta el doble que en sala tradicional."""

    tipo = "VIP"

    @property
    def precio_base(self) -> Decimal:
        return self.PRECIO_TRADICIONAL * 2


_TIPOS = {"tradicional": SalaTradicional, "3d": Sala3D, "vip": SalaVIP}

# (número, tipo, filas, asientos por fila) de las cuatro salas del cine.
CONFIGURACION_CINE = (
    (1, "tradicional", 8, 10),
    (2, "tradicional", 6, 12),
    (3, "3D", 6, 10),
    (4, "VIP", 4, 6),
)


def crear_sala(tipo: str, numero: int, filas: int, asientos_por_fila: int) -> Sala:
    """Fábrica de salas: construye la subclase de ``Sala`` que corresponde al tipo."""
    clase = _TIPOS.get(tipo.strip().lower())
    if clase is None:
        raise DatoInvalidoError(f"tipo de sala desconocido '{tipo}' (use tradicional, 3D o VIP)")
    return clase(numero, filas, asientos_por_fila)


def crear_salas_del_cine(configuracion=CONFIGURACION_CINE) -> dict:
    """Crea el diccionario ``{número: Sala}`` con las salas del cine."""
    return {num: crear_sala(tipo, num, filas, cols) for num, tipo, filas, cols in configuracion}
