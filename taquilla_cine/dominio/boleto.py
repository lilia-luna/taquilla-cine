"""Boleto vendido."""

from datetime import datetime
from decimal import Decimal

from ..excepciones import CancelacionNoPermitidaError


class Boleto:
    """Un boleto = un asiento de una función, con su folio único.

    Sus datos son de solo lectura: el único cambio permitido después de la venta
    es ``cancelar``.
    """

    ACTIVO = "ACTIVO"
    CANCELADO = "CANCELADO"

    def __init__(self, folio, funcion_id, asiento, tarifa, precio, fecha_venta,
                 estado=ACTIVO, fecha_cancelacion=None, reembolso=None):
        if estado not in (self.ACTIVO, self.CANCELADO):
            raise ValueError(f"estado de boleto desconocido: {estado}")
        self._folio = folio
        self._funcion_id = funcion_id
        self._asiento = asiento
        self._tarifa = tarifa
        self._precio = Decimal(precio)
        self._fecha_venta = fecha_venta
        self._estado = estado
        self._fecha_cancelacion = fecha_cancelacion
        self._reembolso = None if reembolso is None else Decimal(reembolso)

    folio = property(lambda self: self._folio, doc="Folio único del boleto.")
    funcion_id = property(lambda self: self._funcion_id, doc="Función a la que pertenece.")
    asiento = property(lambda self: self._asiento, doc="Asiento vendido (A1, B7...).")
    tarifa = property(lambda self: self._tarifa, doc="Nombre de la tarifa aplicada.")
    precio = property(lambda self: self._precio, doc="Precio pagado.")
    fecha_venta = property(lambda self: self._fecha_venta, doc="Fecha y hora de la venta.")
    estado = property(lambda self: self._estado, doc="ACTIVO o CANCELADO.")
    fecha_cancelacion = property(lambda self: self._fecha_cancelacion, doc="Cuándo se canceló.")
    reembolso = property(lambda self: self._reembolso, doc="Monto reembolsado, si se canceló.")

    @property
    def activo(self) -> bool:
        """True mientras el boleto no se haya cancelado."""
        return self._estado == self.ACTIVO

    def cancelar(self, ahora: datetime, reembolso: Decimal) -> None:
        """Marca el boleto como cancelado y registra el reembolso."""
        if not self.activo:
            raise CancelacionNoPermitidaError(f"el boleto {self._folio} ya estaba cancelado")
        self._estado = self.CANCELADO
        self._fecha_cancelacion = ahora
        self._reembolso = Decimal(reembolso)

    def a_dict(self) -> dict:
        """Representación simple para guardar en JSON."""
        return {
            "folio": self._folio,
            "funcion_id": self._funcion_id,
            "asiento": self._asiento,
            "tarifa": self._tarifa,
            "precio": str(self._precio),
            "fecha_venta": self._fecha_venta.isoformat(timespec="minutes"),
            "estado": self._estado,
            "fecha_cancelacion": (
                self._fecha_cancelacion.isoformat(timespec="minutes") if self._fecha_cancelacion else None
            ),
            "reembolso": None if self._reembolso is None else str(self._reembolso),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> "Boleto":
        """Reconstruye un boleto desde ``a_dict``; puede lanzar KeyError/ValueError."""
        cancelacion = datos.get("fecha_cancelacion")
        return cls(
            folio=datos["folio"],
            funcion_id=datos["funcion_id"],
            asiento=datos["asiento"],
            tarifa=datos["tarifa"],
            precio=datos["precio"],
            fecha_venta=datetime.fromisoformat(datos["fecha_venta"]),
            estado=datos.get("estado", cls.ACTIVO),
            fecha_cancelacion=datetime.fromisoformat(cancelacion) if cancelacion else None,
            reembolso=datos.get("reembolso"),
        )
