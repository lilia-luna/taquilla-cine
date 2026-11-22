"""Reporte diario de ventas y ocupación."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..excepciones import ArchivoError
from ..utilidades import dinero, nombre_dia
from .cartelera import Cartelera
from .taquilla import Taquilla


@dataclass
class ReporteDia:
    """Datos del reporte de un día (se calcula una vez y luego se da formato)."""

    fecha: date
    por_pelicula: dict = field(default_factory=dict)  # título -> [boletos, ingresos] 
    por_sala: dict = field(default_factory=dict)      # número -> [boletos, ingresos] 
    funciones: list = field(default_factory=list)     # (función, vendidos, capacidad, porcentaje) 
    cancelados: int = 0
    reembolsos: Decimal = Decimal(0)

    @property
    def total_boletos(self) -> int:
        """Boletos vendidos (no cancelados) en el día."""
        return sum(v[0] for v in self.por_pelicula.values())

    @property
    def total_ingresos(self) -> Decimal:
        """Ingresos del día por boletos vigentes."""
        return sum((v[1] for v in self.por_pelicula.values()), Decimal(0))


class Reportes:
    """Calcula y escribe el reporte de un día (por fecha de la función)."""

    def __init__(self, cartelera: Cartelera, taquilla: Taquilla):
        self._cartelera = cartelera
        self._taquilla = taquilla

    def generar(self, dia: date) -> ReporteDia:
        """Boletos e ingresos por película y por sala, y ocupación de cada función."""
        reporte = ReporteDia(dia)
        for numero in sorted(self._cartelera.salas):
            reporte.por_sala[numero] = [0, Decimal(0)]
        for funcion in self._cartelera.funciones_del_dia(dia):
            todos = self._taquilla.boletos_de_funcion(funcion.id, solo_activos=False)
            activos = [b for b in todos if b.activo]
            ingresos = sum((b.precio for b in activos), Decimal(0))
            acumulado = reporte.por_pelicula.setdefault(funcion.pelicula.titulo, [0, Decimal(0)])
            acumulado[0] += len(activos)
            acumulado[1] += ingresos
            sala = reporte.por_sala[funcion.sala.numero]
            sala[0] += len(activos)
            sala[1] += ingresos
            reporte.funciones.append((funcion, len(activos), funcion.sala.capacidad, 100.0 * len(activos) / funcion.sala.capacidad))
            for boleto in todos:
                if not boleto.activo:
                    reporte.cancelados += 1
                    reporte.reembolsos += boleto.reembolso or Decimal(0)
        reporte.por_pelicula = dict(sorted(reporte.por_pelicula.items()))
        return reporte

    @staticmethod
    def a_texto(reporte: ReporteDia) -> str:
        """Da formato de texto al reporte."""
        salas = {}
        titulo = f"REPORTE DEL DIA {reporte.fecha:%Y-%m-%d} ({nombre_dia(reporte.fecha)})"
        lineas = [titulo, "=" * len(titulo), "",
                  f"Boletos vendidos: {reporte.total_boletos}",
                  f"Ingresos:         {dinero(reporte.total_ingresos)}",
                  f"Cancelaciones:    {reporte.cancelados} (reembolsos {dinero(reporte.reembolsos)})", ""]
        lineas += ["POR PELICULA", f"{'Pelicula':<28}{'Boletos':>8}{'Ingresos':>14}"]
        for nombre, (boletos, ingresos) in reporte.por_pelicula.items():
            lineas.append(f"{nombre:<28}{boletos:>8}{dinero(ingresos):>14}")
        if not reporte.por_pelicula:
            lineas.append("(no hay funciones ese dia)")
        lineas += ["", "POR SALA", f"{'Sala':<28}{'Boletos':>8}{'Ingresos':>14}"]
        for funcion, *_ in reporte.funciones:
            salas[funcion.sala.numero] = str(funcion.sala)
        for numero, (boletos, ingresos) in reporte.por_sala.items():
            etiqueta = salas.get(numero, f"Sala {numero}")
            lineas.append(f"{etiqueta:<28}{boletos:>8}{dinero(ingresos):>14}")
        lineas += ["", "OCUPACION POR FUNCION",
                   f"{'Id':<6}{'Hora':<7}{'Pelicula':<24}{'Sala':<6}{'Vendidos':>10}{'Ocupacion':>11}"]
        for funcion, vendidos, capacidad, porcentaje in reporte.funciones:
            lineas.append(
                f"{funcion.id:<6}{funcion.inicio:%H:%M}  {funcion.pelicula.titulo:<24}"
                f"{funcion.sala.numero:<6}{f'{vendidos}/{capacidad}':>10}{porcentaje:>10.1f}%"
            )
        return "\n".join(lineas) + "\n"

    def escribir(self, reporte: ReporteDia, destino) -> Path:
        """Guarda el reporte en un archivo de texto y devuelve su ruta."""
        ruta = Path(destino)
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(self.a_texto(reporte), encoding="utf-8")
        except OSError as error:
            raise ArchivoError(f"no se pudo escribir el reporte en '{ruta}': {error.strerror or error}") from None
        return ruta
