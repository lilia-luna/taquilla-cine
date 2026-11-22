import unittest
from datetime import datetime
from decimal import Decimal

from taquilla_cine.excepciones import (AsientoInvalidoError, AsientoOcupadoError, CancelacionNoPermitidaError,
                                       DatoInvalidoError, FolioNoEncontradoError, FuncionNoEncontradaError,
                                       TarifaNoPermitidaError, VentaCerradaError)
from taquilla_cine.servicios import Reportes, SolicitudAsiento
from tests.utiles import ANTES, taquilla_demo


def pedir(*textos):
    return [SolicitudAsiento(*t.split(":")) if ":" in t else SolicitudAsiento(t) for t in textos]


class PruebasVenta(unittest.TestCase):
    def setUp(self):
        self.t = taquilla_demo()

    def test_venta_multiple_con_tarifas_y_folios_unicos(self):
        boletos = self.t.vender("F001", pedir("A1:general", "A2:estudiante", "A3:adulto_mayor", "A4:nino"), ANTES)
        self.assertEqual([b.precio for b in boletos], [Decimal(x) for x in ("80", "56", "40", "48")])
        self.assertEqual(len({b.folio for b in boletos}), 4)
        self.assertEqual(self.t.cartelera.obtener("F001").cantidad_ocupados(), 4)

    def test_asiento_ocupado_se_rechaza_y_no_vende_nada(self):
        self.t.vender("F001", pedir("A1"), ANTES)
        with self.assertRaises(AsientoOcupadoError) as ctx:
            self.t.vender("F001", pedir("B1", "A1"), ANTES)
        self.assertEqual(ctx.exception.asientos, ["A1"])
        self.assertFalse(self.t.cartelera.obtener("F001").esta_ocupado("B1"))  # todo o nada

    def test_rechazos_de_datos(self):
        casos = [
            ("F001", pedir("Z9"), AsientoInvalidoError),
            ("F001", pedir("A1", "a1"), AsientoInvalidoError),
            ("F001", [], DatoInvalidoError),
            ("F001", pedir("A1:vip"), TarifaNoPermitidaError),
            ("F004", pedir("A1:nino"), TarifaNoPermitidaError),
            ("F003", pedir("A1:nino"), TarifaNoPermitidaError),
            ("F005", pedir("A1:estudiante"), TarifaNoPermitidaError),
            ("F999", pedir("A1"), FuncionNoEncontradaError),
        ]
        for funcion, solicitud, error in casos:
            with self.assertRaises(error, msg=f"{funcion} {solicitud}"):
                self.t.vender(funcion, solicitud, ANTES)
        self.assertEqual(self.t.todos_los_boletos(), [])  # nada se vendió

    def test_no_se_vende_una_vez_iniciada_la_funcion(self):
        self.t.vender("F001", pedir("A1"), datetime(2026, 11, 27, 13, 59))
        with self.assertRaises(VentaCerradaError):
            self.t.vender("F001", pedir("A2"), datetime(2026, 11, 27, 14, 0))

    def test_estudiante_entre_semana_si_aplica(self):
        self.assertEqual(self.t.vender("F001", pedir("A1:estudiante"), ANTES)[0].precio, Decimal(56))  # viernes


class PruebasCancelacion(unittest.TestCase):
    def setUp(self):
        self.t = taquilla_demo()
        self.boleto = self.t.vender("F001", pedir("A1:estudiante"), ANTES)[0]

    def test_cancela_justo_30_minutos_antes_con_reembolso(self):
        b = self.t.cancelar(self.boleto.folio, datetime(2026, 11, 27, 13, 30))
        self.assertEqual(b.reembolso, Decimal(56))
        self.assertFalse(self.t.cartelera.obtener("F001").esta_ocupado("A1"))

    def test_no_cancela_con_menos_de_30_minutos(self):
        with self.assertRaises(CancelacionNoPermitidaError):
            self.t.cancelar(self.boleto.folio, datetime(2026, 11, 27, 13, 31))
        self.assertTrue(self.boleto.activo)
        self.assertTrue(self.t.cartelera.obtener("F001").esta_ocupado("A1"))

    def test_no_cancela_dos_veces_ni_folio_inexistente(self):
        self.t.cancelar(self.boleto.folio.lower(), ANTES)  # el folio no distingue mayúsculas
        with self.assertRaises(CancelacionNoPermitidaError):
            self.t.cancelar(self.boleto.folio, ANTES)
        with self.assertRaises(FolioNoEncontradoError):
            self.t.cancelar("FOL-999999", ANTES)

    def test_asiento_cancelado_puede_volver_a_venderse(self):
        self.t.cancelar(self.boleto.folio, ANTES)
        nuevo = self.t.vender("F001", pedir("A1"), ANTES)[0]
        self.assertNotEqual(nuevo.folio, self.boleto.folio)  # los folios nunca se reutilizan
        self.assertEqual(self.t.verificar_consistencia(), [])


class PruebasReporte(unittest.TestCase):
    def test_reporte_por_pelicula_sala_y_ocupacion(self):
        t = taquilla_demo()
        t.vender("F001", pedir("A1", "A2:nino"), ANTES)      # Galaxia, sala 1: 80 + 48
        t.vender("F002", pedir("A1:adulto_mayor"), ANTES)    # Luna, sala 3: 55
        b = t.vender("F004", pedir("A1"), ANTES)[0]          # Cena, VIP: 160 (se cancelará)
        t.vender("F005", pedir("A1"), ANTES)                 # Galaxia, sábado: no cuenta en viernes
        t.cancelar(b.folio, ANTES)
        r = Reportes(t.cartelera, t).generar(datetime(2026, 11, 27).date())
        self.assertEqual(r.por_pelicula["Galaxia"], [2, Decimal(128)])
        self.assertEqual(r.por_pelicula["Luna"], [1, Decimal(55)])
        self.assertEqual(r.por_pelicula["Cena"], [0, Decimal(0)])
        self.assertEqual(r.por_sala[1], [2, Decimal(128)])
        self.assertEqual(r.por_sala[3], [1, Decimal(55)])
        self.assertEqual((r.total_boletos, r.total_ingresos), (3, Decimal(183)))
        self.assertEqual((r.cancelados, r.reembolsos), (1, Decimal(160)))
        ocupacion = {f.id: round(p, 1) for f, _, _, p in r.funciones}
        self.assertEqual(ocupacion["F001"], 2.5)
        self.assertEqual(ocupacion["F002"], round(100 / 60, 1))


if __name__ == "__main__":
    unittest.main()
