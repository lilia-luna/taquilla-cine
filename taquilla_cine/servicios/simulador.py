"""Simulación de la venta de un estreno con hilos.

Cinco puntos de venta (cuatro taquillas y la venta en línea) atienden en
paralelo a una cola de compradores generados al azar. Al terminar se comprueba
que ningún asiento se vendió dos veces y que los totales coinciden con los
mapas de asientos.
"""

import queue
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..dominio.funcion import Funcion
from ..dominio.tarifas import tarifas_disponibles
from ..excepciones import AsientoOcupadoError, DatoInvalidoError, TaquillaError, TarifaNoPermitidaError
from .taquilla import SolicitudAsiento, Taquilla

PUNTOS_DE_VENTA = ("Taquilla 1", "Taquilla 2", "Taquilla 3", "Taquilla 4", "Venta en linea")


@dataclass(frozen=True)
class Comprador:
    """Comprador generado al azar: quiere de 1 a 4 asientos de una misma función."""

    numero: int
    funcion_id: str
    asientos: int


@dataclass
class _Estadistica:
    """Contadores de un punto de venta (cada hilo escribe solo los suyos)."""

    ventas: int = 0
    boletos: int = 0
    ingresos: Decimal = Decimal(0)
    sin_lugar: int = 0
    abandonos: int = 0
    conflictos: int = 0
    errores: list = field(default_factory=list)


@dataclass
class ResultadoSimulacion:
    """Resumen de la simulación y verificación final."""

    compradores: int
    ventas: int
    sin_lugar: int
    abandonos: int
    conflictos: int
    boletos: int
    ingresos: Decimal
    por_punto: dict
    segundos: float
    problemas: list
    errores: list = field(default_factory=list)

    @property
    def correcta(self) -> bool:
        """True si no se detectó ninguna inconsistencia."""
        return not self.problemas


class SimuladorEstreno:
    """Ejecuta la simulación de venta concurrente."""

    def __init__(self, taquilla: Taquilla, compradores: int = 300, semilla=None,
                 retardo_max: float = 0.002, max_intentos: int = 5):
        if compradores < 1:
            raise DatoInvalidoError("el número de compradores debe ser al menos 1")
        self._taquilla = taquilla
        self._cantidad = compradores
        self._semilla = semilla
        self._retardo_max = retardo_max
        self._max_intentos = max_intentos

    def generar_compradores(self, funciones: list) -> list:
        """Crea los compradores: función al azar y de 1 a 4 asientos."""
        azar = random.Random(self._semilla)
        return [Comprador(i + 1, azar.choice(funciones).id, azar.randint(1, 4)) for i in range(self._cantidad)]

    def ejecutar(self, funciones: list, ahora: datetime) -> ResultadoSimulacion:
        """Atiende a todos los compradores con 5 hilos y verifica el resultado."""
        if not funciones:
            raise DatoInvalidoError("no hay funciones para simular")
        antes = {f.id: f.cantidad_ocupados() for f in funciones}
        folios_previos = {b.folio for b in self._taquilla.todos_los_boletos()}

        cola = queue.Queue()
        for comprador in self.generar_compradores(funciones):
            cola.put(comprador)
        estadisticas = {punto: _Estadistica() for punto in PUNTOS_DE_VENTA}
        hilos = [
            threading.Thread(target=self._trabajar, name=punto, args=(punto, cola, ahora, estadisticas[punto]))
            for punto in PUNTOS_DE_VENTA
        ]
        inicio = time.perf_counter()
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        segundos = time.perf_counter() - inicio

        return self._resumir(funciones, antes, folios_previos, estadisticas, segundos)

    # --- trabajo de cada punto de venta -----------------------------------
    def _trabajar(self, punto: str, cola, ahora: datetime, est: _Estadistica) -> None:
        azar = random.Random(f"{self._semilla}-{punto}")  # generador propio: random.Random no se comparte
        while True:
            try:
                comprador = cola.get_nowait()
            except queue.Empty:
                return
            try:
                self._atender(comprador, azar, ahora, est)
            except Exception as error:  # un hilo nunca debe morir con traceback
                est.errores.append(f"comprador {comprador.numero}: error inesperado: {error}")

    def _atender(self, comprador: Comprador, azar, ahora: datetime, est: _Estadistica) -> None:
        funcion = self._taquilla.cartelera.obtener(comprador.funcion_id)
        for _ in range(self._max_intentos):
            libres = funcion.asientos_libres()
            if len(libres) < comprador.asientos:
                est.sin_lugar += 1
                return
            elegidos = azar.sample(libres, comprador.asientos)
            permitidas = self._tarifas_permitidas(funcion)
            solicitudes = [SolicitudAsiento(a, azar.choice(permitidas)) for a in elegidos]
            if self._retardo_max:
                time.sleep(azar.uniform(0, self._retardo_max))  # el cajero tarda en cobrar: otros compran mientras tanto
            try:
                boletos = self._taquilla.vender(funcion.id, solicitudes, ahora)
            except AsientoOcupadoError:
                est.conflictos += 1  # otro punto de venta ganó ese asiento; se reintenta
                continue
            except TaquillaError as error:
                est.errores.append(f"comprador {comprador.numero}: {error}")
                return
            est.ventas += 1
            est.boletos += len(boletos)
            est.ingresos += sum((b.precio for b in boletos), Decimal(0))
            return
        est.abandonos += 1

    @staticmethod
    def _tarifas_permitidas(funcion: Funcion) -> list:
        permitidas = []
        for tarifa in tarifas_disponibles():
            try:
                tarifa.validar(funcion)
                permitidas.append(tarifa.nombre)
            except TarifaNoPermitidaError:
                pass
        return permitidas

    # --- verificación -----------------------------------------------------
    def _resumir(self, funciones, antes, folios_previos, estadisticas, segundos) -> ResultadoSimulacion:
        problemas = list(self._taquilla.verificar_consistencia())
        errores = [e for est in estadisticas.values() for e in est.errores]
        nuevos = [b for b in self._taquilla.todos_los_boletos() if b.folio not in folios_previos and b.activo]
        boletos = sum(e.boletos for e in estadisticas.values())
        ingresos = sum((e.ingresos for e in estadisticas.values()), Decimal(0))
        nuevos_en_mapas = sum(f.cantidad_ocupados() - antes[f.id] for f in funciones)

        if len(nuevos) != boletos:
            problemas.append(f"los puntos de venta reportan {boletos} boletos pero se registraron {len(nuevos)}")
        if nuevos_en_mapas != boletos:
            problemas.append(f"los puntos de venta reportan {boletos} boletos pero los mapas ganaron {nuevos_en_mapas} asientos")
        if sum((b.precio for b in nuevos), Decimal(0)) != ingresos:
            problemas.append("los ingresos reportados no coinciden con los boletos registrados")

        return ResultadoSimulacion(
            compradores=self._cantidad,
            ventas=sum(e.ventas for e in estadisticas.values()),
            sin_lugar=sum(e.sin_lugar for e in estadisticas.values()),
            abandonos=sum(e.abandonos for e in estadisticas.values()),
            conflictos=sum(e.conflictos for e in estadisticas.values()),
            boletos=boletos,
            ingresos=ingresos,
            por_punto={p: (e.ventas, e.boletos) for p, e in estadisticas.items()},
            segundos=segundos,
            problemas=problemas,
            errores=errores,
        )
