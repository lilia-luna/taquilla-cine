import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from taquilla_cine.interfaz import Aplicacion, ejecutar
from taquilla_cine.interfaz.menu import Menu
from tests.utiles import DATOS


class PruebasCLI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def correr(self, *args):
        salida, error = io.StringIO(), io.StringIO()
        with redirect_stdout(salida), redirect_stderr(error):
            codigo = ejecutar(["--datos", self.dir, *args])
        return codigo, salida.getvalue(), error.getvalue()

    def test_flujo_completo_entre_ejecuciones(self):
        antes = ["--ahora", "2026-11-26 12:00"]
        codigo, out, _ = self.correr("cargar", str(DATOS / "cartelera_semana1.csv"))
        self.assertEqual(codigo, 0)
        self.assertIn("48 funciones aceptadas", out)
        _, out, _ = self.correr(*antes, "funciones", "--fecha", "2026-11-27")
        self.assertIn("F013", out)
        codigo, out, _ = self.correr(*antes, "vender", "F013", "A1:general", "A2:estudiante")
        self.assertEqual(codigo, 0)
        self.assertIn("Total: $136.00", out)
        self.assertTrue((Path(self.dir) / "boletos" / "FOL-000001.txt").exists())
        _, out, _ = self.correr("mapa", "F013")
        self.assertIn("[X] [X]", out)
        codigo, out, _ = self.correr("--ahora", "2026-11-27 13:30", "cancelar", "FOL-000002")
        self.assertIn("Reembolso: $56.00", out)
        codigo, out, _ = self.correr("--ahora", "2026-11-27 12:00", "reporte", "--fecha", "2026-11-27")
        self.assertIn("Boletos vendidos: 1", out)
        self.assertTrue((Path(self.dir) / "reportes" / "reporte_2026-11-27.txt").exists())

    def test_errores_son_mensajes_no_tracebacks(self):
        self.correr("cargar", str(DATOS / "cartelera_semana1.csv"))
        casos = [
            ("cargar", "no_existe.csv"),
            ("cargar", str(DATOS / "cartelera_danada.csv")),
            ("mapa", "F999"),
            ("vender", "F013", "Z99"),
            ("vender", "F013", "A1:vip"),
            ("cancelar", "FOL-000123"),
            ("simular", "--fecha", "2030-01-01"),
        ]
        for caso in casos:
            codigo, _, error = self.correr("--ahora", "2026-11-26 12:00", *caso)
            self.assertEqual(codigo, 1, caso)
            self.assertTrue(error.startswith("Error:"), (caso, error))
            self.assertNotIn("Traceback", error)

    def test_simular_por_cli(self):
        self.correr("cargar", str(DATOS / "cartelera_semana1.csv"))
        codigo, out, _ = self.correr("--ahora", "2026-11-26 12:00", "simular", "--fecha", "2026-11-27",
                                     "--pelicula", "galaxia perdida", "--semilla", "7")
        self.assertEqual(codigo, 0)
        self.assertIn("VERIFICACION: correcta", out)
        codigo, out, _ = self.correr("--ahora", "2026-11-26 12:00", "mapa", "F013")
        self.assertIn("[X]", out)  # las ventas simuladas se conservaron

    def test_menu_con_entradas_validas_e_invalidas(self):
        respuestas = iter(["x", "1", str(DATOS / "cartelera_semana1.csv"), "8", "2026-11-26 12:00",
                           "4", "F013", "A1:general", "4", "F013", "A1", "2", "2026-99-99", "0"])
        salida = []
        app = Aplicacion(self.dir, salida=salida.append, salida_error=salida.append)
        codigo = Menu(app, entrada=lambda _: next(respuestas), salida=salida.append).ejecutar()
        texto = "\n".join(map(str, salida))
        self.assertEqual(codigo, 0)
        self.assertIn("Opción no válida", texto)
        self.assertIn("Venta registrada", texto)
        self.assertIn("Asiento(s) ocupado(s): A1", texto)
        self.assertIn("fecha inválida", texto)

    def test_menu_termina_con_fin_de_entrada(self):
        def sin_entrada(_):
            raise EOFError
        app = Aplicacion(self.dir, salida=lambda *_: None)
        self.assertEqual(Menu(app, entrada=sin_entrada, salida=lambda *_: None).ejecutar(), 0)


if __name__ == "__main__":
    unittest.main()
