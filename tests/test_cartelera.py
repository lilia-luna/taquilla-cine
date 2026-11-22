import tempfile
import unittest
from pathlib import Path

from taquilla_cine.dominio import crear_salas_del_cine
from taquilla_cine.excepciones import ArchivoDanadoError, ArchivoError
from taquilla_cine.servicios import Cartelera
from tests.utiles import DATOS


def nueva():
    return Cartelera(crear_salas_del_cine())


class PruebasCargaCSV(unittest.TestCase):
    def test_cartelera_valida_se_acepta_completa(self):
        r = nueva().cargar_csv(DATOS / "cartelera_semana1.csv")
        self.assertEqual((len(r.aceptadas), len(r.rechazos)), (48, 0))

    def test_archivo_con_errores_informa_cada_renglon(self):
        c = nueva()
        c.cargar_csv(DATOS / "cartelera_semana1.csv")
        r = c.cargar_csv(DATOS / "cartelera_con_errores.csv")
        self.assertEqual(len(r.aceptadas), 3)
        motivos = {x.renglon: x.motivo for x in r.rechazos}
        self.assertEqual(sorted(motivos), [3, 4, 5, 6, 7, 8, 10, 11, 12, 14, 15])
        self.assertIn("sala '7' no existe", motivos[3])
        self.assertIn("fecha inválida", motivos[4])
        self.assertIn("fecha inválida", motivos[5])
        self.assertIn("hora inválida", motivos[6])
        self.assertIn("se traslapa", motivos[7])
        self.assertIn("se traslapa", motivos[8])      # solo 10 min de limpieza
        self.assertIn("clasificación", motivos[10])
        self.assertIn("duración", motivos[11])
        self.assertIn("campos", motivos[12])
        self.assertIn("título", motivos[14])
        self.assertIn("F013", motivos[15])            # choca con la cartelera ya cargada

    def test_cargar_dos_veces_rechaza_todo_por_traslape(self):
        c = nueva()
        c.cargar_csv(DATOS / "cartelera_semana1.csv")
        r = c.cargar_csv(DATOS / "cartelera_semana1.csv")
        self.assertEqual((len(r.aceptadas), len(r.rechazos)), (0, 48))

    def test_varios_errores_en_un_renglon_se_reportan_juntos(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "x.csv"
            ruta.write_text("pelicula,clasificacion,duracion,sala,fecha,hora\nX,Z,abc,9,hoy,tarde\n", encoding="utf-8")
            r = nueva().cargar_csv(ruta)
        self.assertEqual(len(r.rechazos), 1)
        self.assertEqual(r.rechazos[0].motivo.count(";"), 4)

    def test_archivos_malos_lanzan_errores_controlados(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with self.assertRaises(ArchivoError):
                nueva().cargar_csv(d / "no_existe.csv")
            with self.assertRaises(ArchivoDanadoError):
                nueva().cargar_csv(DATOS / "cartelera_danada.csv")
            (d / "vacio.csv").write_text("", encoding="utf-8")
            with self.assertRaises(ArchivoDanadoError):
                nueva().cargar_csv(d / "vacio.csv")
            (d / "binario.csv").write_bytes(b"\xff\xfe\x00\x81\x82pelicula")
            with self.assertRaises(ArchivoDanadoError):
                nueva().cargar_csv(d / "binario.csv")
            with self.assertRaises(ArchivoError):
                nueva().cargar_csv(d)  # una carpeta, no un archivo

    def test_encabezado_con_acentos_y_mayusculas(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "x.csv"
            ruta.write_text("Película,Clasificación,Duración,Sala,Fecha,Hora\nX,a,90,1,2026-11-27,10:00\n", encoding="utf-8")
            r = nueva().cargar_csv(ruta)
        self.assertEqual((len(r.aceptadas), len(r.rechazos)), (1, 0))


if __name__ == "__main__":
    unittest.main()
