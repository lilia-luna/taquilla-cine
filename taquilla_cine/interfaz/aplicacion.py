"""Aplicación: conecta las operaciones del sistema con la terminal.

Tanto el modo de comandos (argparse) como el menú de texto llaman a los mismos
métodos de esta clase, así que ambos se comportan igual.
"""

import sys
from datetime import date, datetime
from pathlib import Path

from ..dominio.salas import crear_salas_del_cine
from ..excepciones import ArchivoError, DatoInvalidoError
from ..persistencia.repositorio import RepositorioJSON
from ..servicios.impresor import ImpresorBoletos
from ..servicios.reportes import Reportes
from ..servicios.simulador import SimuladorEstreno
from ..servicios.taquilla import SolicitudAsiento
from ..utilidades import dinero
from . import formato


def _imprimir_error(mensaje: str) -> None:
    print(mensaje, file=sys.stderr)


class Aplicacion:
    """Operaciones de alto nivel: cargar, consultar, vender, cancelar, reportar y simular."""

    def __init__(self, directorio="estado", ahora=None, salida=print, salida_error=_imprimir_error):
        """
        :param directorio: carpeta donde se guardan datos, boletos y reportes.
        :param ahora: fecha y hora fijas de las operaciones; si es None se usa el reloj.
        """
        self._salida = salida
        self._salida_error = salida_error
        self._ahora_fijo = ahora
        self._repositorio = RepositorioJSON(directorio)
        self._cartelera, self._taquilla, advertencias = self._repositorio.cargar(crear_salas_del_cine())
        for aviso in advertencias:
            self._salida_error(f"Aviso: {aviso}")
        self._impresor = ImpresorBoletos(self._repositorio.directorio / "boletos")
        self._reportes = Reportes(self._cartelera, self._taquilla)

    # --- reloj ------------------------------------------------------------
    @property
    def ahora(self) -> datetime:
        """Fecha y hora de las operaciones (fijas si se indicó ``--ahora``)."""
        return self._ahora_fijo or datetime.now().replace(second=0, microsecond=0)

    @ahora.setter
    def ahora(self, valor) -> None:
        self._ahora_fijo = valor

    def _guardar(self) -> None:
        try:
            self._repositorio.guardar(self._cartelera, self._taquilla)
        except ArchivoError as error:
            self._salida_error(f"Aviso: {error}. Los cambios solo existen en esta ejecución.")

    # --- operaciones ------------------------------------------------------
    def cargar(self, ruta) -> None:
        """Carga un CSV de cartelera e informa cada renglón rechazado."""
        resultado = self._cartelera.cargar_csv(ruta)
        self._salida(f"Archivo '{ruta}': {len(resultado.aceptadas)} funciones aceptadas, "
                     f"{len(resultado.rechazos)} renglones rechazados.")
        for rechazo in resultado.rechazos:
            self._salida(f"  Renglón {rechazo.renglon} rechazado: {rechazo.motivo}")
            self._salida(f"      contenido: {rechazo.contenido}")
        if resultado.aceptadas:
            self._guardar()

    def funciones(self, dia: date = None, todas: bool = False) -> None:
        """Muestra las funciones de un día (o todas)."""
        dia = dia or self.ahora.date()
        lista = self._cartelera.funciones() if todas else self._cartelera.funciones_del_dia(dia)
        if not lista:
            self._salida("No hay funciones registradas" + ("." if todas else f" el {dia:%Y-%m-%d}."))
            return
        self._salida(formato.lista_de_funciones(lista))

    def mapa(self, funcion_id: str) -> None:
        """Muestra el mapa de asientos de una función."""
        self._salida(formato.mapa_de_asientos(self._cartelera.obtener(funcion_id)))

    def vender(self, funcion_id: str, textos: list) -> None:
        """Vende asientos. Cada texto es ``ASIENTO`` o ``ASIENTO:TARIFA`` (ej. ``B4:estudiante``)."""
        solicitudes = []
        for texto in textos:
            asiento, _, tarifa = texto.partition(":")
            solicitudes.append(SolicitudAsiento(asiento, tarifa or "general"))
        boletos = self._taquilla.vender(funcion_id, solicitudes, self.ahora)
        funcion = self._cartelera.obtener(funcion_id)
        self._guardar()
        self._salida(f"Venta registrada: {formato.encabezado_funcion(funcion)}")
        total = 0
        for boleto in boletos:
            total += boleto.precio
            try:
                ruta = self._impresor.escribir(boleto, funcion)
                destino = f"-> {ruta}"
            except ArchivoError as error:
                destino = f"(boleto vendido, pero no se pudo crear el archivo: {error})"
            self._salida(f"  {boleto.folio}  {boleto.asiento:<4}{boleto.tarifa:<13}{dinero(boleto.precio):>10}  {destino}")
        self._salida(f"Total: {dinero(total)}")

    def cancelar(self, folio: str) -> None:
        """Cancela un boleto e indica el reembolso."""
        boleto = self._taquilla.cancelar(folio, self.ahora)
        funcion = self._cartelera.obtener(boleto.funcion_id)
        self._guardar()
        try:
            self._impresor.escribir(boleto, funcion)
        except ArchivoError as error:
            self._salida_error(f"Aviso: {error}")
        self._salida(f"Boleto {boleto.folio} cancelado (asiento {boleto.asiento} de {funcion.id}). "
                     f"Reembolso: {dinero(boleto.reembolso)}")

    def reporte(self, dia: date = None, salida=None) -> None:
        """Genera el reporte de un día en un archivo y lo muestra."""
        dia = dia or self.ahora.date()
        reporte = self._reportes.generar(dia)
        destino = Path(salida) if salida else self._repositorio.directorio / "reportes" / f"reporte_{dia:%Y-%m-%d}.txt"
        ruta = self._reportes.escribir(reporte, destino)
        self._salida(self._reportes.a_texto(reporte))
        self._salida(f"Reporte guardado en {ruta}")

    def simular(self, dia: date, pelicula: str = None, compradores: int = 300, semilla=None, guardar: bool = True) -> None:
        """Simula la venta de un estreno con 5 puntos de venta concurrentes."""
        funciones = self._cartelera.funciones_del_dia(dia)
        if pelicula:
            funciones = [f for f in funciones if f.pelicula.titulo.lower() == pelicula.strip().lower()]
        if not funciones:
            raise DatoInvalidoError("no hay funciones para simular con esos criterios (revise la fecha y el título)")
        self._salida(f"Simulando estreno: {len(funciones)} funciones, {compradores} compradores, "
                     f"5 puntos de venta, operación a las {self.ahora:%Y-%m-%d %H:%M}...")
        resultado = SimuladorEstreno(self._taquilla, compradores, semilla).ejecutar(funciones, self.ahora)
        self._salida(formato.resumen_simulacion(resultado))
        if guardar:
            self._guardar()
            self._salida("Resultado guardado (use --sin-guardar para no conservar las ventas simuladas).")
