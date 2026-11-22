"""Modelo de dominio: salas, tarifas, películas, funciones y boletos."""

from .boleto import Boleto
from .funcion import CLASIFICACIONES, INTERVALO_LIMPIEZA, Funcion, Pelicula
from .salas import Sala, Sala3D, SalaTradicional, SalaVIP, crear_sala, crear_salas_del_cine
from .tarifas import (Tarifa, TarifaAdultoMayor, TarifaEstudiante, TarifaGeneral, TarifaNino,
                      nombres_de_tarifas, obtener_tarifa, tarifas_disponibles)

__all__ = [
    "Boleto", "CLASIFICACIONES", "INTERVALO_LIMPIEZA", "Funcion", "Pelicula", "Sala", "Sala3D",
    "SalaTradicional", "SalaVIP", "crear_sala", "crear_salas_del_cine", "Tarifa", "TarifaAdultoMayor",
    "TarifaEstudiante", "TarifaGeneral", "TarifaNino", "nombres_de_tarifas", "obtener_tarifa",
    "tarifas_disponibles",
]
