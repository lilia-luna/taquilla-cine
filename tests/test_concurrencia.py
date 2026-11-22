import tempfile
import threading
import unittest

from taquilla_cine.dominio import crear_salas_del_cine
from taquilla_cine.excepciones import AsientoOcupadoError
from taquilla_cine.persistencia import RepositorioJSON
from taquilla_cine.servicios import Cartelera, SimuladorEstreno, SolicitudAsiento, Taquilla
from tests.utiles import ANTES, DATOS, taquilla_demo


class PruebasConcurrencia(unittest.TestCase):
    def test_muchos_hilos_por_el_mismo_asiento_solo_uno_gana(self):
        t = taquilla_demo()
        ganadores, perdedores = [], []
        barrera = threading.Barrier(30)

        def comprar():
            barrera.wait()
            try:
                ganadores.append(t.vender("F001", [SolicitudAsiento("A1")], ANTES))
            except AsientoOcupadoError:
                perdedores.append(1)

        hilos = [threading.Thread(target=comprar) for _ in range(30)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual((len(ganadores), len(perdedores)), (1, 29))
        self.assertEqual(t.verificar_consistencia(), [])

    def test_folios_unicos_con_hilos(self):
        t = taquilla_demo()
        sala = t.cartelera.obtener("F001").sala.asientos()[:60]

        def comprar(lote):
            for a in lote:
                t.vender("F001", [SolicitudAsiento(a)], ANTES)

        hilos = [threading.Thread(target=comprar, args=(sala[i::6],)) for i in range(6)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        folios = [b.folio for b in t.todos_los_boletos()]
        self.assertEqual((len(folios), len(set(folios))), (60, 60))

    def test_simulacion_de_estreno_es_consistente(self):
        cartelera = Cartelera(crear_salas_del_cine())
        cartelera.cargar_csv(DATOS / "cartelera_semana1.csv")
        taquilla = Taquilla(cartelera)
        funciones = [f for f in cartelera.funciones_del_dia(ANTES.date().replace(day=27))
                     if f.pelicula.titulo == "Galaxia Perdida"]
        for semilla in (1, 2, 3):
            resultado = SimuladorEstreno(taquilla, compradores=300, semilla=semilla).ejecutar(funciones, ANTES)
            self.assertTrue(resultado.correcta, resultado.problemas)
            self.assertEqual(resultado.compradores, 300)
            self.assertEqual(resultado.ventas + resultado.sin_lugar + resultado.abandonos + len(resultado.errores), 300)
        self.assertEqual(taquilla.verificar_consistencia(), [])
        ocupados = sum(f.cantidad_ocupados() for f in funciones)
        self.assertEqual(ocupados, len([b for b in taquilla.todos_los_boletos() if b.activo]))
        with tempfile.TemporaryDirectory() as d:  # y lo simulado se puede guardar y recuperar igual
            repo = RepositorioJSON(d)
            repo.guardar(cartelera, taquilla)
            _, otra, avisos = repo.cargar(crear_salas_del_cine())
            self.assertEqual((avisos, otra.verificar_consistencia()), ([], []))
            self.assertEqual(len(otra.todos_los_boletos()), len(taquilla.todos_los_boletos()))


if __name__ == "__main__":
    unittest.main()
