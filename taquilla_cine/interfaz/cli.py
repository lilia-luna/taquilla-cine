"""Interfaz de línea de comandos con argparse."""

import argparse
import sys

from ..excepciones import DatoInvalidoError, TaquillaError
from ..utilidades import parsear_fecha, parsear_fecha_hora
from .aplicacion import Aplicacion
from .menu import Menu


def _tipo_fecha(texto):
    try:
        return parsear_fecha(texto)
    except DatoInvalidoError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _tipo_fecha_hora(texto):
    try:
        return parsear_fecha_hora(texto)
    except DatoInvalidoError as error:
        raise argparse.ArgumentTypeError(str(error)) from None


def _opciones_globales(parser, subcomando: bool) -> None:
    """Opciones comunes; se aceptan antes o después del comando."""
    suprimir = argparse.SUPPRESS
    parser.add_argument("--datos", default=suprimir if subcomando else "estado", metavar="DIR",
                        help="carpeta donde se guardan los datos del programa (por omisión: estado)")
    parser.add_argument("--ahora", type=_tipo_fecha_hora, default=suprimir if subcomando else None,
                        metavar="'AAAA-MM-DD HH:MM'",
                        help="fecha y hora de la operación, para probar reglas de tiempo (por omisión: reloj)")


def construir_parser() -> argparse.ArgumentParser:
    """Crea el analizador de argumentos con todos los comandos."""
    parser = argparse.ArgumentParser(prog="taquilla", description="Sistema de taquilla de un cine.")
    _opciones_globales(parser, False)
    sub = parser.add_subparsers(dest="comando", metavar="comando")

    def comando(nombre, ayuda):
        p = sub.add_parser(nombre, help=ayuda, description=ayuda)
        _opciones_globales(p, True)
        return p

    p = comando("cargar", "Carga la cartelera semanal desde un archivo CSV.")
    p.add_argument("archivo", help="ruta del CSV (ej. datos/cartelera_semana1.csv)")

    p = comando("funciones", "Muestra las funciones de un día.")
    p.add_argument("--fecha", type=_tipo_fecha, help="AAAA-MM-DD (por omisión: la fecha de --ahora)")
    p.add_argument("--todas", action="store_true", help="muestra todas las funciones de la cartelera")

    p = comando("mapa", "Muestra el mapa de asientos de una función.")
    p.add_argument("funcion", help="id de la función (ej. F014)")

    p = comando("vender", "Vende uno o varios asientos con su tarifa.")
    p.add_argument("funcion", help="id de la función")
    p.add_argument("asientos", nargs="+", metavar="ASIENTO[:TARIFA]",
                   help="ej. A1:general B3:estudiante C5:adulto_mayor D2:nino (sin tarifa = general)")

    p = comando("cancelar", "Cancela un boleto por su folio (hasta 30 min antes).")
    p.add_argument("folio", help="folio del boleto (ej. FOL-000001)")

    p = comando("reporte", "Genera el reporte de un día en un archivo.")
    p.add_argument("--fecha", type=_tipo_fecha, help="AAAA-MM-DD (por omisión: la fecha de --ahora)")
    p.add_argument("--salida", help="ruta del archivo (por omisión: <datos>/reportes/reporte_FECHA.txt)")

    p = comando("simular", "Simula la venta de un estreno con 5 puntos de venta concurrentes.")
    p.add_argument("--fecha", type=_tipo_fecha, required=True, help="día del estreno (AAAA-MM-DD)")
    p.add_argument("--pelicula", help="título de la película (por omisión: todas las funciones del día)")
    p.add_argument("--compradores", type=int, default=300, help="número de compradores (por omisión: 300)")
    p.add_argument("--semilla", type=int, help="semilla del generador aleatorio, para repetir la simulación")
    p.add_argument("--sin-guardar", action="store_true", help="no conserva las ventas simuladas")

    comando("menu", "Abre el menú de texto interactivo (es lo que se ejecuta sin comando).")
    return parser


def ejecutar(argv=None) -> int:
    """Interpreta los argumentos y ejecuta el comando. Devuelve el código de salida."""
    for flujo in (sys.stdout, sys.stderr):  # evita errores de codificación en consolas antiguas
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    args = construir_parser().parse_args(argv)
    try:
        app = Aplicacion(args.datos, args.ahora)
        comando = args.comando or "menu"
        if comando == "cargar":
            app.cargar(args.archivo)
        elif comando == "funciones":
            app.funciones(args.fecha, args.todas)
        elif comando == "mapa":
            app.mapa(args.funcion)
        elif comando == "vender":
            app.vender(args.funcion, args.asientos)
        elif comando == "cancelar":
            app.cancelar(args.folio)
        elif comando == "reporte":
            app.reporte(args.fecha, args.salida)
        elif comando == "simular":
            app.simular(args.fecha, args.pelicula, args.compradores, args.semilla, not args.sin_guardar)
        elif comando == "menu":
            return Menu(app).ejecutar()
        return 0
    except TaquillaError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:  # p. ej. al encadenar con ``| head``
        return 0
    except KeyboardInterrupt:
        print("\nOperación interrumpida.", file=sys.stderr)
        return 130
    except Exception as error:  # último recurso: nunca mostrar un traceback al usuario
        print(f"Error inesperado ({type(error).__name__}): {error}", file=sys.stderr)
        return 2
