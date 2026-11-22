"""Generación del boleto como archivo de texto."""

from pathlib import Path

from ..dominio.boleto import Boleto
from ..dominio.funcion import Funcion
from ..excepciones import ArchivoError
from ..utilidades import dinero, nombre_dia


class ImpresorBoletos:
    """Escribe un archivo ``FOL-xxxxxx.txt`` por cada boleto."""

    def __init__(self, directorio):
        self._directorio = Path(directorio)

    def ruta(self, folio: str) -> Path:
        """Ruta del archivo de un boleto."""
        return self._directorio / f"{folio}.txt"

    @staticmethod
    def texto(boleto: Boleto, funcion: Funcion) -> str:
        """Contenido del boleto."""
        lineas = [
            "=" * 38,
            "            CINE - BOLETO",
            "=" * 38,
            f"Folio:         {boleto.folio}",
            f"Pelicula:      {funcion.pelicula.titulo}",
            f"Clasificacion: {funcion.pelicula.clasificacion}",
            f"Sala:          {funcion.sala}",
            f"Fecha:         {nombre_dia(funcion.inicio.date())} {funcion.inicio:%Y-%m-%d}",
            f"Hora:          {funcion.inicio:%H:%M} (termina {funcion.fin:%H:%M})",
            f"Asiento:       {boleto.asiento}",
            f"Tarifa:        {boleto.tarifa}",
            f"Precio:        {dinero(boleto.precio)}",
            f"Vendido:       {boleto.fecha_venta:%Y-%m-%d %H:%M}",
            f"Estado:        {boleto.estado}",
        ]
        if not boleto.activo:
            lineas.append(f"Cancelado:     {boleto.fecha_cancelacion:%Y-%m-%d %H:%M}")
            lineas.append(f"Reembolso:     {dinero(boleto.reembolso)}")
        lineas.append("=" * 38)
        return "\n".join(lineas) + "\n"

    def escribir(self, boleto: Boleto, funcion: Funcion) -> Path:
        """Crea (o actualiza) el archivo del boleto y devuelve su ruta."""
        ruta = self.ruta(boleto.folio)
        try:
            self._directorio.mkdir(parents=True, exist_ok=True)
            ruta.write_text(self.texto(boleto, funcion), encoding="utf-8")
        except OSError as error:
            raise ArchivoError(f"no se pudo escribir el boleto {boleto.folio}: {error.strerror or error}") from None
        return ruta
