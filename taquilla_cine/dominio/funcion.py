"""Películas y funciones.

Una ``Funcion`` es la proyección de una ``Pelicula`` en una ``Sala`` a cierta
hora. Es el objeto que protege el mapa de asientos: todos los cambios pasan por
``ocupar`` y ``liberar`` y están sincronizados con un candado propio, para que
varios hilos puedan vender al mismo tiempo sin duplicar asientos.
"""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..excepciones import AsientoOcupadoError, DatoInvalidoError
from .salas import Sala

CLASIFICACIONES = ("A", "B", "C")
INTERVALO_LIMPIEZA = timedelta(minutes=20)


@dataclass(frozen=True)
class Pelicula:
    """Película de la cartelera (inmutable)."""

    titulo: str
    clasificacion: str
    duracion: int  # minutos

    def __post_init__(self):
        if not self.titulo or not self.titulo.strip():
            raise DatoInvalidoError("la película no tiene título")
        if self.clasificacion not in CLASIFICACIONES:
            raise DatoInvalidoError(
                f"clasificación '{self.clasificacion}' no válida (use A, B o C)"
            )
        if not isinstance(self.duracion, int) or not 1 <= self.duracion <= 600:
            raise DatoInvalidoError(
                f"duración '{self.duracion}' no válida (use minutos enteros entre 1 y 600)"
            )


class Funcion:
    """Proyección de una película en una sala, con su mapa de asientos."""

    def __init__(self, id_funcion: str, pelicula: Pelicula, sala: Sala, inicio: datetime):
        self._id = id_funcion
        self._pelicula = pelicula
        self._sala = sala
        self._inicio = inicio
        self._ocupados = {}  # asiento -> folio del boleto
        self._lock = threading.RLock()

    @property
    def id(self) -> str:
        """Identificador de la función (F001, F002...)."""
        return self._id

    @property
    def pelicula(self) -> Pelicula:
        """Película que se proyecta."""
        return self._pelicula

    @property
    def sala(self) -> Sala:
        """Sala donde se proyecta."""
        return self._sala

    @property
    def inicio(self) -> datetime:
        """Fecha y hora de inicio."""
        return self._inicio

    @property
    def fin(self) -> datetime:
        """Fecha y hora en que termina la película."""
        return self._inicio + timedelta(minutes=self._pelicula.duracion)

    @property
    def lock(self) -> threading.RLock:
        """Candado de la función, para operaciones compuestas (revisar y ocupar)."""
        return self._lock

    def se_traslapa_con(self, otra: "Funcion") -> bool:
        """True si ambas están en la misma sala y no respetan los 20 min de limpieza."""
        if self._sala.numero != otra.sala.numero:
            return False
        return self._inicio < otra.fin + INTERVALO_LIMPIEZA and otra.inicio < self.fin + INTERVALO_LIMPIEZA

    # --- mapa de asientos -------------------------------------------------
    def esta_ocupado(self, asiento: str) -> bool:
        """True si el asiento ya fue vendido."""
        with self._lock:
            return asiento in self._ocupados

    def ocupar(self, asiento: str, folio: str) -> None:
        """Marca un asiento como vendido; lanza AsientoOcupadoError si ya lo estaba."""
        asiento = self._sala.normalizar_asiento(asiento)
        with self._lock:
            if asiento in self._ocupados:
                raise AsientoOcupadoError([asiento])
            self._ocupados[asiento] = folio

    def liberar(self, asiento: str) -> None:
        """Libera un asiento (por una cancelación)."""
        with self._lock:
            self._ocupados.pop(asiento, None)

    def asientos_ocupados(self) -> dict:
        """Copia del mapa ``{asiento: folio}``."""
        with self._lock:
            return dict(self._ocupados)

    def asientos_libres(self) -> list:
        """Asientos disponibles, en orden."""
        with self._lock:
            return [a for a in self._sala.asientos() if a not in self._ocupados]

    def cantidad_ocupados(self) -> int:
        """Número de asientos vendidos."""
        with self._lock:
            return len(self._ocupados)

    def porcentaje_ocupacion(self) -> float:
        """Porcentaje de la sala ocupado (0 a 100)."""
        return 100.0 * self.cantidad_ocupados() / self._sala.capacidad

    def __str__(self) -> str:
        return f"{self._id} {self._pelicula.titulo} ({self._sala}) {self._inicio:%Y-%m-%d %H:%M}"
