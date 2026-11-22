"""Excepciones propias del sistema.

Todas heredan de :class:`TaquillaError`, de modo que la capa de interfaz puede
capturar cualquier error *esperado* con un solo ``except`` y mostrar un mensaje
claro al usuario en lugar de un traceback.
"""


class TaquillaError(Exception):
    """Clase base de todos los errores controlados del sistema."""


class DatoInvalidoError(TaquillaError):
    """Un dato recibido (texto, fecha, número...) no cumple las reglas."""


class RenglonInvalidoError(DatoInvalidoError):
    """Un renglón del CSV de la cartelera tiene uno o más datos inválidos."""


class SalaInexistenteError(DatoInvalidoError):
    """Se hizo referencia a una sala que el cine no tiene."""


class TraslapeError(DatoInvalidoError):
    """Una función se traslapa con otra de la misma sala (incluye la limpieza)."""


class ArchivoError(TaquillaError):
    """No se pudo leer o escribir un archivo."""


class ArchivoDanadoError(ArchivoError):
    """Un archivo existe pero su contenido no tiene el formato esperado."""


class FuncionNoEncontradaError(TaquillaError):
    """No existe una función con el identificador indicado."""


class AsientoInvalidoError(DatoInvalidoError):
    """El asiento no existe en la sala o está repetido en la solicitud."""


class AsientoOcupadoError(TaquillaError):
    """Alguno de los asientos solicitados ya fue vendido."""

    def __init__(self, asientos):
        self.asientos = list(asientos)
        super().__init__("Asiento(s) ocupado(s): " + ", ".join(self.asientos))


class TarifaNoPermitidaError(TaquillaError):
    """La tarifa no existe o no puede aplicarse a esa función."""


class VentaCerradaError(TaquillaError):
    """La función ya comenzó; no se pueden vender más boletos."""


class FolioNoEncontradoError(TaquillaError):
    """No existe ningún boleto con ese folio."""


class CancelacionNoPermitidaError(TaquillaError):
    """El boleto ya está cancelado o ya pasó el límite para cancelarlo."""
