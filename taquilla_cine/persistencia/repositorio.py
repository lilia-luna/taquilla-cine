"""Persistencia en archivos JSON.

Se guardan dos archivos en el directorio de datos: ``cartelera.json`` y
``ventas.json``. Los asientos ocupados *no* se guardan: se reconstruyen a partir
de los boletos activos, así hay una sola fuente de verdad y no pueden quedar
inconsistentes.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from ..dominio.boleto import Boleto
from ..dominio.funcion import Pelicula
from ..excepciones import ArchivoError, TaquillaError
from ..servicios.cartelera import Cartelera
from ..servicios.taquilla import Taquilla

_ERRORES_DE_DATO = (TaquillaError, KeyError, TypeError, ValueError, ArithmeticError, AttributeError)


class RepositorioJSON:
    """Guarda y recupera la cartelera y las ventas."""

    ARCHIVO_CARTELERA = "cartelera.json"
    ARCHIVO_VENTAS = "ventas.json"

    def __init__(self, directorio):
        self._directorio = Path(directorio)

    @property
    def directorio(self) -> Path:
        """Directorio donde se guardan los archivos."""
        return self._directorio

    # --- lectura ----------------------------------------------------------
    def cargar(self, salas: dict):
        """Reconstruye ``(cartelera, taquilla, advertencias)`` desde los archivos.

        Un archivo faltante significa "todavía no hay datos". Un archivo dañado
        se aparta con la extensión ``.corrupto`` y se informa en las advertencias;
        las entradas inválidas se omiten una por una. Nunca lanza excepciones por
        datos malos.
        """
        advertencias = []
        cartelera = Cartelera(salas)
        datos = self._leer(self.ARCHIVO_CARTELERA, advertencias)
        if datos is not None:
            self._restaurar_cartelera(cartelera, datos, advertencias)
        taquilla = Taquilla(cartelera)
        datos = self._leer(self.ARCHIVO_VENTAS, advertencias)
        if datos is not None:
            self._restaurar_ventas(taquilla, datos, advertencias)
        return cartelera, taquilla, advertencias

    def _leer(self, nombre: str, advertencias: list):
        ruta = self._directorio / nombre
        if not ruta.exists():
            return None
        try:
            with ruta.open(encoding="utf-8") as archivo:
                datos = json.load(archivo)
            if not isinstance(datos, dict):
                raise ValueError("el contenido no es un objeto JSON")
            return datos
        except (OSError, ValueError) as error:  # JSONDecodeError y UnicodeDecodeError son ValueError
            destino = ruta.with_name(nombre + ".corrupto")
            try:
                os.replace(ruta, destino)
                donde = f"se conservó como {destino.name}"
            except OSError:
                donde = "no se pudo apartar"
            advertencias.append(f"{nombre} está dañado ({error}); {donde} y se continúa sin esos datos")
            return None

    @staticmethod
    def _lista(datos: dict, clave: str, archivo: str, advertencias: list) -> list:
        """Devuelve ``datos[clave]`` si es una lista; si no, avisa y devuelve una lista vacía."""
        valor = datos.get(clave, [])
        if not isinstance(valor, list):
            advertencias.append(f"{archivo}: '{clave}' no es una lista; se ignoró")
            return []
        return valor

    def _restaurar_cartelera(self, cartelera: Cartelera, datos: dict, advertencias: list) -> None:
        for entrada in self._lista(datos, "funciones", "cartelera.json", advertencias):
            try:
                pelicula = Pelicula(entrada["pelicula"], entrada["clasificacion"], entrada["duracion"])
                cartelera.agregar(pelicula, entrada["sala"], datetime.fromisoformat(entrada["inicio"]),
                                  id_funcion=entrada["id"])
            except _ERRORES_DE_DATO as error:
                ident = entrada.get("id", "?") if isinstance(entrada, dict) else "?"
                advertencias.append(f"cartelera.json: se omitió la función {ident} ({error})")
        try:
            cartelera.fijar_siguiente_id(int(datos.get("siguiente_id", 1)))
        except (TypeError, ValueError):
            advertencias.append("cartelera.json: 'siguiente_id' inválido; se recalculó")

    def _restaurar_ventas(self, taquilla: Taquilla, datos: dict, advertencias: list) -> None:
        huerfanos = 0
        for entrada in self._lista(datos, "boletos", "ventas.json", advertencias):
            try:
                taquilla.restaurar_boleto(Boleto.desde_dict(entrada))
            except _ERRORES_DE_DATO as error:
                ident = entrada.get("folio", "?") if isinstance(entrada, dict) else "?"
                advertencias.append(f"ventas.json: se omitió el boleto {ident} ({error})")
                huerfanos += 1
        if huerfanos:
            try:  # guarda una copia antes de que el siguiente guardado reescriba el archivo
                shutil.copy2(self._directorio / self.ARCHIVO_VENTAS,
                             self._directorio / (self.ARCHIVO_VENTAS + ".respaldo"))
            except OSError:
                pass
        try:
            taquilla.fijar_siguiente_folio(int(datos.get("siguiente_folio", 1)))
        except (TypeError, ValueError):
            advertencias.append("ventas.json: 'siguiente_folio' inválido; se recalculó")

    # --- escritura --------------------------------------------------------
    def guardar(self, cartelera: Cartelera, taquilla: Taquilla) -> None:
        """Guarda cartelera y ventas. Lanza ArchivoError si no se puede escribir."""
        self._escribir(self.ARCHIVO_CARTELERA, cartelera.exportar())
        self._escribir(self.ARCHIVO_VENTAS, taquilla.exportar())

    def _escribir(self, nombre: str, datos: dict) -> None:
        destino = self._directorio / nombre
        temporal = destino.with_name(nombre + ".tmp")
        try:
            self._directorio.mkdir(parents=True, exist_ok=True)
            with temporal.open("w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
            os.replace(temporal, destino)  # reemplazo atómico: nunca queda un JSON a medias
        except OSError as error:
            raise ArchivoError(f"no se pudo guardar {nombre} en '{self._directorio}': {error.strerror or error}") from None
