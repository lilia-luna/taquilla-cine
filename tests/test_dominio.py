import unittest
from datetime import datetime
from decimal import Decimal

from taquilla_cine.dominio import (Pelicula, Sala, crear_sala, crear_salas_del_cine, obtener_tarifa)
from taquilla_cine.excepciones import AsientoInvalidoError, DatoInvalidoError, TarifaNoPermitidaError
from tests.utiles import cartelera_demo


class PruebasSalas(unittest.TestCase):
    def test_precios_base(self):
        salas = crear_salas_del_cine()
        self.assertEqual(salas[1].precio_base, Decimal(80))
        self.assertEqual(salas[3].precio_base, Decimal(110))  # 3D: +$30
        self.assertEqual(salas[4].precio_base, Decimal(160))  # VIP: el doble

    def test_sala_es_abstracta(self):
        with self.assertRaises(TypeError):
            Sala(1, 4, 4)

    def test_tipo_desconocido(self):
        with self.assertRaises(DatoInvalidoError):
            crear_sala("imax", 9, 4, 4)

    def test_asientos(self):
        sala = crear_sala("tradicional", 1, 3, 4)
        self.assertEqual(sala.capacidad, 12)
        self.assertEqual(sala.normalizar_asiento(" b3 "), "B3")
        for malo in ("D1", "A5", "A0", "11", "", "AA1", "A-1"):
            with self.assertRaises(AsientoInvalidoError, msg=malo):
                sala.normalizar_asiento(malo)


class PruebasTarifas(unittest.TestCase):
    def setUp(self):
        self.c = cartelera_demo()

    def precio(self, funcion, tarifa):
        f = self.c.obtener(funcion)
        t = obtener_tarifa(tarifa)
        t.validar(f)
        return t.precio(f.sala.precio_base)

    def test_precios_tradicional(self):
        self.assertEqual(self.precio("F001", "general"), Decimal("80"))
        self.assertEqual(self.precio("F001", "estudiante"), Decimal("56"))
        self.assertEqual(self.precio("F001", "adulto_mayor"), Decimal("40"))
        self.assertEqual(self.precio("F001", "nino"), Decimal("48"))

    def test_descuento_se_aplica_sobre_precio_de_sala(self):
        self.assertEqual(self.precio("F002", "general"), Decimal("110"))
        self.assertEqual(self.precio("F002", "nino"), Decimal("66"))
        self.assertEqual(self.precio("F004", "adulto_mayor"), Decimal("80"))
        self.assertEqual(self.precio("F004", "estudiante"), Decimal("112"))

    def test_estudiante_solo_entre_semana(self):
        with self.assertRaises(TarifaNoPermitidaError):
            self.precio("F005", "estudiante")  # sábado
        self.assertEqual(self.precio("F005", "adulto_mayor"), Decimal("40"))

    def test_nino_no_en_vip_ni_clasificacion_c(self):
        with self.assertRaises(TarifaNoPermitidaError):
            self.precio("F004", "nino")
        with self.assertRaises(TarifaNoPermitidaError):
            self.precio("F003", "nino")

    def test_nombres_flexibles_y_desconocidos(self):
        self.assertEqual(obtener_tarifa("Niño").nombre, "nino")
        self.assertEqual(obtener_tarifa("Adulto Mayor").nombre, "adulto_mayor")
        with self.assertRaises(TarifaNoPermitidaError):
            obtener_tarifa("vip")


class PruebasFunciones(unittest.TestCase):
    def test_pelicula_valida_sus_datos(self):
        for args in (("", "A", 90), ("X", "D", 90), ("X", "A", 0), ("X", "A", "90")):
            with self.assertRaises(DatoInvalidoError):
                Pelicula(*args)

    def test_limpieza_de_20_minutos(self):
        from taquilla_cine.servicios import Cartelera
        from taquilla_cine.excepciones import TraslapeError
        c = Cartelera(crear_salas_del_cine())
        p = Pelicula("X", "A", 100)  # termina a las 15:40
        c.agregar(p, 1, datetime(2026, 11, 27, 14, 0))
        for hora, minuto in ((15, 59), (15, 40), (14, 30)):
            with self.assertRaises(TraslapeError):
                c.agregar(p, 1, datetime(2026, 11, 27, hora, minuto))
        c.agregar(p, 1, datetime(2026, 11, 27, 16, 0))  # justo 20 minutos después: válido
        c.agregar(p, 2, datetime(2026, 11, 27, 14, 0))  # otra sala: válido


if __name__ == "__main__":
    unittest.main()
