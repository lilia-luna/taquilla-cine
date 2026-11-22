import json
import shutil
import tempfile
import unittest
from pathlib import Path

from taquilla_cine.dominio import crear_salas_del_cine
from taquilla_cine.excepciones import ArchivoError
from taquilla_cine.persistencia import RepositorioJSON
from taquilla_cine.servicios import SolicitudAsiento
from tests.utiles import ANTES, DATOS, taquilla_demo


class PruebasPersistencia(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ida_y_vuelta_conserva_cartelera_ventas_y_folios(self):
        t = taquilla_demo()
        b = t.vender("F001", [SolicitudAsiento("A1", "nino"), SolicitudAsiento("A2")], ANTES)
        t.cancelar(b[1].folio, ANTES)
        repo = RepositorioJSON(self.dir)
        repo.guardar(t.cartelera, t)
        cartelera, t2, avisos = repo.cargar(crear_salas_del_cine())
        self.assertEqual(avisos, [])
        self.assertEqual(len(cartelera.funciones()), 5)
        self.assertEqual(t2.boleto(b[0].folio).precio, b[0].precio)
        self.assertFalse(t2.boleto(b[1].folio).activo)
        self.assertEqual(t2.cartelera.obtener("F001").asientos_ocupados(), {"A1": b[0].folio})
        nuevo = t2.vender("F001", [SolicitudAsiento("A2")], ANTES)[0]
        self.assertEqual(nuevo.folio, "FOL-000003")  # continúa la numeración
        self.assertEqual(t2.verificar_consistencia(), [])

    def test_sin_archivos_empieza_vacio(self):
        cartelera, taquilla, avisos = RepositorioJSON(self.dir / "nuevo").cargar(crear_salas_del_cine())
        self.assertEqual((cartelera.funciones(), taquilla.todos_los_boletos(), avisos), ([], [], []))

    def test_json_danado_se_aparta_y_el_programa_continua(self):
        shutil.copytree(DATOS / "estado_corrupto", self.dir / "e")
        cartelera, taquilla, avisos = RepositorioJSON(self.dir / "e").cargar(crear_salas_del_cine())
        self.assertEqual([f.id for f in cartelera.funciones()], ["F001"])  # F002 tenía sala 9
        self.assertEqual(taquilla.todos_los_boletos(), [])
        self.assertTrue((self.dir / "e" / "ventas.json.corrupto").exists())
        self.assertEqual(len(avisos), 2)

    def test_contenidos_raros_no_rompen(self):
        repo = RepositorioJSON(self.dir)
        for contenido in ("[]", "null", "", "\x00\x01", '{"funciones": 5}', '{"funciones": [1, "x", null]}',
                          '{"boletos": [{"folio": "FOL-000001"}]}'):
            (self.dir / "cartelera.json").write_text(contenido, encoding="utf-8")
            (self.dir / "ventas.json").write_text(contenido, encoding="utf-8")
            try:
                repo.cargar(crear_salas_del_cine())
            except Exception as error:  # pragma: no cover
                self.fail(f"cargar falló con {contenido!r}: {error!r}")

    def test_boleto_huerfano_se_omite_y_se_respalda(self):
        repo = RepositorioJSON(self.dir)
        (self.dir / "cartelera.json").write_text('{"siguiente_id": 1, "funciones": []}', encoding="utf-8")
        boleto = {"folio": "FOL-000007", "funcion_id": "F001", "asiento": "A1", "tarifa": "general",
                  "precio": "80", "fecha_venta": "2026-11-26T12:00"}
        (self.dir / "ventas.json").write_text(json.dumps({"siguiente_folio": 8, "boletos": [boleto]}), encoding="utf-8")
        _, taquilla, avisos = repo.cargar(crear_salas_del_cine())
        self.assertEqual(taquilla.todos_los_boletos(), [])
        self.assertTrue(any("FOL-000007" in a for a in avisos))
        self.assertTrue((self.dir / "ventas.json.respaldo").exists())

    def test_no_se_puede_escribir_lanza_error_controlado(self):
        archivo = self.dir / "es_un_archivo"
        archivo.write_text("x")
        t = taquilla_demo()
        with self.assertRaises(ArchivoError):
            RepositorioJSON(archivo / "dentro").guardar(t.cartelera, t)


if __name__ == "__main__":
    unittest.main()
