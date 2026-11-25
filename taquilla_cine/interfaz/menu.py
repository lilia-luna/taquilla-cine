"""Menú de texto interactivo."""

from ..excepciones import TaquillaError
from ..utilidades import parsear_fecha, parsear_fecha_hora
from .aplicacion import Aplicacion

OPCIONES = """
===== TAQUILLA DEL CINE =====
 1. Cargar cartelera desde CSV
 2. Ver funciones de un día
 3. Ver mapa de asientos de una función
 4. Vender boletos
 5. Cancelar un boleto
 6. Reporte de un día
 7. Simular venta de estreno
 8. Cambiar fecha y hora de las operaciones
 0. Salir
"""


class Menu:
    """Ciclo de menú; recibe ``entrada`` para poder probarlo sin teclado."""

    def __init__(self, app: Aplicacion, entrada=input, salida=print):
        self._app = app
        self._entrada = entrada
        self._salida = salida

    def _preguntar(self, texto: str, defecto: str = "") -> str:
        sufijo = f" [{defecto}]" if defecto else ""
        respuesta = self._entrada(f"{texto}{sufijo}: ").strip()
        return respuesta or defecto

    def ejecutar(self) -> int:
        """Muestra el menú hasta que la persona elija salir."""
        acciones = {
            "1": self._cargar, "2": self._funciones, "3": self._mapa, "4": self._vender,
            "5": self._cancelar, "6": self._reporte, "7": self._simular, "8": self._cambiar_reloj,
        }
        while True:
            self._salida(OPCIONES)
            self._salida(f"Fecha y hora de las operaciones: {self._app.ahora:%Y-%m-%d %H:%M}")
            try:
                opcion = self._entrada("Elija una opción: ").strip()
            except (EOFError, KeyboardInterrupt):
                self._salida("\nHasta luego.")
                return 0
            if opcion == "0":
                self._salida("Hasta luego.")
                return 0
            accion = acciones.get(opcion)
            if accion is None:
                self._salida("Opción no válida; escriba un número del menú.")
                continue
            try:
                accion()
            except TaquillaError as error:
                self._salida(f"Error: {error}")
            except (EOFError, KeyboardInterrupt):
                self._salida("\nOperación cancelada.")

    def _cargar(self):
        self._app.cargar(self._preguntar("Ruta del CSV", "datos/cartelera_semana1.csv"))

    def _funciones(self):
        self._app.funciones(parsear_fecha(self._preguntar("Fecha (AAAA-MM-DD)", f"{self._app.ahora:%Y-%m-%d}")))

    def _mapa(self):
        self._app.mapa(self._preguntar("Id de la función (ej. F014)"))

    def _vender(self):
        funcion = self._preguntar("Id de la función")
        texto = self._preguntar("Asientos con tarifa, separados por espacio (ej. A1:general B2:nino)")
        self._app.vender(funcion, texto.split())

    def _cancelar(self):
        self._app.cancelar(self._preguntar("Folio del boleto (ej. FOL-000001)"))

    def _reporte(self):
        self._app.reporte(parsear_fecha(self._preguntar("Fecha (AAAA-MM-DD)", f"{self._app.ahora:%Y-%m-%d}")))

    def _simular(self):
        dia = parsear_fecha(self._preguntar("Fecha del estreno (AAAA-MM-DD)"))
        pelicula = self._preguntar("Título de la película (vacío = todas las del día)")
        self._app.simular(dia, pelicula or None, guardar=self._preguntar("¿Conservar las ventas simuladas? (s/n)", "n").lower() == "s")

    def _cambiar_reloj(self):
        self._app.ahora = parsear_fecha_hora(self._preguntar("Nueva fecha y hora (AAAA-MM-DD HH:MM)"))
