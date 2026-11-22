"""Taquilla: vende y cancela boletos de forma segura entre hilos.

Orden de candados (para evitar interbloqueos): primero el candado de la
*función* y después el del *registro* de boletos. Nunca se toma un candado de
función estando dentro del registro.
"""

import re
import threading
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..dominio.boleto import Boleto
from ..dominio.tarifas import obtener_tarifa
from ..excepciones import (AsientoInvalidoError, AsientoOcupadoError, CancelacionNoPermitidaError,
                           DatoInvalidoError, FolioNoEncontradoError, FuncionNoEncontradaError,
                           VentaCerradaError)
from .cartelera import Cartelera

ANTICIPO_CANCELACION = timedelta(minutes=30)
_PATRON_FOLIO = re.compile(r"^FOL-(\d+)$")


@dataclass(frozen=True)
class SolicitudAsiento:
    """Un asiento que el cliente quiere comprar y la tarifa con la que paga."""

    asiento: str
    tarifa: str = "general"


class Taquilla:
    """Fachada de las operaciones de venta, cancelación y consulta de boletos."""

    def __init__(self, cartelera: Cartelera):
        self._cartelera = cartelera
        self._boletos = {}
        self._siguiente_folio = 1
        self._lock_registro = threading.Lock()

    @property
    def cartelera(self) -> Cartelera:
        """Cartelera sobre la que vende esta taquilla."""
        return self._cartelera

    # --- venta ------------------------------------------------------------
    def vender(self, funcion_id: str, solicitudes, ahora: datetime) -> list:
        """Vende uno o varios asientos de una función; es *todo o nada*.

        Si algún asiento no existe, está ocupado o su tarifa no está permitida,
        no se vende ninguno. Puede llamarse desde varios hilos a la vez.

        :param ahora: fecha y hora de la operación (se inyecta para poder probar
            reglas que dependen del tiempo).
        :return: lista de boletos generados, uno por asiento.
        """
        funcion = self._cartelera.obtener(funcion_id)
        solicitudes = list(solicitudes)
        if not solicitudes:
            raise DatoInvalidoError("indique al menos un asiento")
        if ahora >= funcion.inicio:
            raise VentaCerradaError(
                f"la función {funcion.id} comenzó a las {funcion.inicio:%H:%M}; ya no se venden boletos"
            )

        preparadas, vistos = [], set()
        for solicitud in solicitudes:  # validaciones que no dependen de otros hilos
            asiento = funcion.sala.normalizar_asiento(solicitud.asiento)
            if asiento in vistos:
                raise AsientoInvalidoError(f"el asiento {asiento} está repetido en la solicitud")
            vistos.add(asiento)
            tarifa = obtener_tarifa(solicitud.tarifa)
            tarifa.validar(funcion)
            preparadas.append((asiento, tarifa, tarifa.precio(funcion.sala.precio_base)))

        with funcion.lock:  # revisar y ocupar debe ser una sola operación atómica
            ocupados = [a for a, _, _ in preparadas if funcion.esta_ocupado(a)]
            if ocupados:
                raise AsientoOcupadoError(ocupados)
            boletos = []
            for asiento, tarifa, precio in preparadas:
                folio = self._nuevo_folio()
                boleto = Boleto(folio, funcion.id, asiento, tarifa.nombre, precio, ahora)
                funcion.ocupar(asiento, folio)
                with self._lock_registro:
                    self._boletos[folio] = boleto
                boletos.append(boleto)
        return boletos

    def _nuevo_folio(self) -> str:
        with self._lock_registro:
            folio = f"FOL-{self._siguiente_folio:06d}"
            self._siguiente_folio += 1
            return folio

    # --- cancelación ------------------------------------------------------
    def cancelar(self, folio: str, ahora: datetime) -> Boleto:
        """Cancela un boleto hasta 30 minutos antes de la función.

        El reembolso es el 100 % de lo pagado. El asiento queda libre.
        """
        boleto = self.boleto(folio)
        funcion = self._cartelera.obtener(boleto.funcion_id)
        with funcion.lock:
            if not boleto.activo:
                raise CancelacionNoPermitidaError(f"el boleto {boleto.folio} ya estaba cancelado")
            limite = funcion.inicio - ANTICIPO_CANCELACION
            if ahora > limite:
                raise CancelacionNoPermitidaError(
                    f"ya no se puede cancelar: el límite era {limite:%Y-%m-%d %H:%M} "
                    "(30 minutos antes de la función)"
                )
            funcion.liberar(boleto.asiento)
            boleto.cancelar(ahora, boleto.precio)
        return boleto

    # --- consultas --------------------------------------------------------
    def boleto(self, folio: str) -> Boleto:
        """Busca un boleto por folio o lanza FolioNoEncontradoError."""
        try:
            return self._boletos[(folio or "").strip().upper()]
        except KeyError:
            raise FolioNoEncontradoError(f"no existe ningún boleto con el folio '{folio}'") from None

    def todos_los_boletos(self) -> list:
        """Copia de la lista de todos los boletos (activos y cancelados)."""
        with self._lock_registro:
            return list(self._boletos.values())

    def boletos_de_funcion(self, funcion_id: str, solo_activos: bool = True) -> list:
        """Boletos de una función."""
        return [b for b in self.todos_los_boletos()
                if b.funcion_id == funcion_id and (b.activo or not solo_activos)]

    # --- consistencia y persistencia -------------------------------------
    def verificar_consistencia(self) -> list:
        """Compara boletos activos contra mapas de asientos; devuelve los problemas hallados."""
        problemas = []
        activos = defaultdict(list)
        for boleto in self.todos_los_boletos():
            if boleto.activo:
                activos[boleto.funcion_id].append(boleto)
        conocidas = {f.id for f in self._cartelera.funciones()}
        for funcion_id in activos:
            if funcion_id not in conocidas:
                problemas.append(f"hay boletos de una función inexistente: {funcion_id}")
        for funcion in self._cartelera.funciones():
            boletos = activos.get(funcion.id, [])
            asientos = [b.asiento for b in boletos]
            if len(asientos) != len(set(asientos)):
                problemas.append(f"{funcion.id}: algún asiento se vendió más de una vez")
            mapa = funcion.asientos_ocupados()
            if set(asientos) != set(mapa):
                problemas.append(
                    f"{funcion.id}: el mapa tiene {len(mapa)} asientos ocupados "
                    f"pero hay {len(set(asientos))} boletos activos"
                )
            elif any(mapa[b.asiento] != b.folio for b in boletos):
                problemas.append(f"{funcion.id}: algún asiento del mapa apunta a otro folio")
        return problemas

    def exportar(self) -> dict:
        """Estado serializable, tomado de forma consistente aun con ventas en curso."""
        funciones = sorted(self._cartelera.funciones(), key=lambda f: f.id)
        with ExitStack() as pila:
            for funcion in funciones:  # mismo orden que vender/cancelar: función, luego registro
                pila.enter_context(funcion.lock)
            with self._lock_registro:
                return {
                    "siguiente_folio": self._siguiente_folio,
                    "boletos": [b.a_dict() for b in sorted(self._boletos.values(), key=lambda b: b.folio)],
                }

    def restaurar_boleto(self, boleto: Boleto) -> None:
        """Reincorpora un boleto guardado (y su asiento, si sigue activo)."""
        funcion = self._cartelera.obtener(boleto.funcion_id)
        if boleto.folio in self._boletos:
            raise DatoInvalidoError(f"el folio {boleto.folio} está repetido")
        if boleto.activo:
            funcion.ocupar(boleto.asiento, boleto.folio)
        self._boletos[boleto.folio] = boleto
        coincidencia = _PATRON_FOLIO.match(boleto.folio)
        if coincidencia:
            self._siguiente_folio = max(self._siguiente_folio, int(coincidencia.group(1)) + 1)

    def fijar_siguiente_folio(self, numero: int) -> None:
        """Usado al restaurar datos, para que los folios nunca se repitan."""
        self._siguiente_folio = max(self._siguiente_folio, numero)
