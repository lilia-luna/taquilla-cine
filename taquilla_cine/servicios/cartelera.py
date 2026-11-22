"""Cartelera: colección de funciones y carga semanal desde CSV."""

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ..dominio.funcion import CLASIFICACIONES, Funcion, Pelicula
from ..dominio.salas import Sala
from ..excepciones import (ArchivoDanadoError, ArchivoError, DatoInvalidoError,
                           FuncionNoEncontradaError, RenglonInvalidoError, SalaInexistenteError,
                           TaquillaError, TraslapeError)
from ..utilidades import parsear_fecha, parsear_hora

COLUMNAS = ("pelicula", "clasificacion", "duracion", "sala", "fecha", "hora")
_PATRON_ID = re.compile(r"^F(\d+)$")


@dataclass(frozen=True)
class Rechazo:
    """Renglón del CSV que no se pudo aceptar, con su motivo."""

    renglon: int
    motivo: str
    contenido: str


@dataclass
class ResultadoCarga:
    """Resultado de cargar un CSV: funciones aceptadas y renglones rechazados."""

    aceptadas: list = field(default_factory=list)
    rechazos: list = field(default_factory=list)


def _normalizar_columna(nombre: str) -> str:
    texto = (nombre or "").strip().lower()
    return texto.replace("í", "i").replace("é", "e").replace("ó", "o").replace("á", "a")


class Cartelera:
    """Agrega las funciones del cine y garantiza que no se traslapen."""

    def __init__(self, salas: dict):
        self._salas = dict(salas)
        self._funciones = {}
        self._siguiente_id = 1

    @property
    def salas(self) -> dict:
        """Salas del cine ``{número: Sala}``."""
        return dict(self._salas)

    def sala(self, numero: int) -> Sala:
        """Devuelve una sala o lanza SalaInexistenteError."""
        try:
            return self._salas[numero]
        except KeyError:
            raise SalaInexistenteError(
                f"la sala {numero} no existe (salas disponibles: {min(self._salas)} a {max(self._salas)})"
            ) from None

    @property
    def siguiente_id(self) -> int:
        """Número que tendrá la próxima función creada."""
        return self._siguiente_id

    def fijar_siguiente_id(self, numero: int) -> None:
        """Usado al restaurar datos guardados, para no repetir identificadores."""
        self._siguiente_id = max(self._siguiente_id, numero)

    def agregar(self, pelicula: Pelicula, numero_sala: int, inicio: datetime, id_funcion=None) -> Funcion:
        """Agrega una función; lanza SalaInexistenteError o TraslapeError si no es válida."""
        sala = self.sala(numero_sala)
        nuevo_id = id_funcion or f"F{self._siguiente_id:03d}"
        candidata = Funcion(nuevo_id, pelicula, sala, inicio)
        for existente in self._funciones.values():
            if candidata.se_traslapa_con(existente):
                raise TraslapeError(
                    f"se traslapa con {existente.id} '{existente.pelicula.titulo}' en la sala {numero_sala} "
                    f"({existente.inicio:%H:%M}-{existente.fin:%H:%M}); entre funciones debe haber "
                    "20 minutos de limpieza"
                )
        if nuevo_id in self._funciones:
            raise DatoInvalidoError(f"ya existe una función con el id {nuevo_id}")
        self._funciones[nuevo_id] = candidata
        coincidencia = _PATRON_ID.match(nuevo_id)
        if coincidencia:
            self._siguiente_id = max(self._siguiente_id, int(coincidencia.group(1)) + 1)
        return candidata

    def obtener(self, id_funcion: str) -> Funcion:
        """Busca una función por id (sin distinguir mayúsculas)."""
        try:
            return self._funciones[(id_funcion or "").strip().upper()]
        except KeyError:
            raise FuncionNoEncontradaError(
                f"no existe la función '{id_funcion}' (consulte los ids con el comando 'funciones')"
            ) from None

    def funciones(self) -> list:
        """Todas las funciones ordenadas por fecha, hora y sala."""
        return sorted(self._funciones.values(), key=lambda f: (f.inicio, f.sala.numero))

    def funciones_del_dia(self, dia: date) -> list:
        """Funciones que inician en el día indicado."""
        return [f for f in self.funciones() if f.inicio.date() == dia]

    def exportar(self) -> dict:
        """Estado serializable (para guardar en JSON)."""
        return {
            "siguiente_id": self._siguiente_id,
            "funciones": [
                {
                    "id": f.id,
                    "pelicula": f.pelicula.titulo,
                    "clasificacion": f.pelicula.clasificacion,
                    "duracion": f.pelicula.duracion,
                    "sala": f.sala.numero,
                    "inicio": f.inicio.isoformat(timespec="minutes"),
                }
                for f in sorted(self._funciones.values(), key=lambda f: f.id)
            ],
        }

    # --- carga desde CSV --------------------------------------------------
    def cargar_csv(self, ruta) -> ResultadoCarga:
        """Carga la cartelera semanal desde un CSV.

        Acepta las funciones válidas y devuelve en ``rechazos`` cada renglón
        inválido con su motivo. Lanza ArchivoError / ArchivoDanadoError solo si
        el archivo no existe, no se puede leer o no tiene las columnas esperadas.
        """
        renglones = self._leer_renglones(Path(ruta))
        resultado = ResultadoCarga()
        for numero, texto, valores in renglones:
            try:
                pelicula, sala, inicio = self._validar_renglon(valores)
                resultado.aceptadas.append(self.agregar(pelicula, sala, inicio))
            except TaquillaError as error:
                resultado.rechazos.append(Rechazo(numero, str(error), texto))
        return resultado

    @staticmethod
    def _leer_renglones(ruta: Path) -> list:
        """Lee todo el CSV antes de agregar nada, para no dejar cargas a medias."""
        try:
            with ruta.open(newline="", encoding="utf-8-sig") as archivo:
                lector = csv.reader(archivo)
                encabezado = next(lector, None)
                if not encabezado:
                    raise ArchivoDanadoError(f"el archivo '{ruta}' está vacío")
                columnas = [_normalizar_columna(c) for c in encabezado]
                faltantes = [c for c in COLUMNAS if c not in columnas]
                if faltantes:
                    raise ArchivoDanadoError(
                        f"al archivo '{ruta}' le faltan las columnas: {', '.join(faltantes)} "
                        f"(encabezado esperado: {','.join(COLUMNAS)})"
                    )
                renglones = []
                for fila in lector:
                    if not any(celda.strip() for celda in fila):
                        continue
                    texto = ",".join(fila)
                    if len(fila) != len(columnas):
                        renglones.append((lector.line_num, texto, None))
                    else:
                        renglones.append((lector.line_num, texto, dict(zip(columnas, fila))))
                return renglones
        except FileNotFoundError:
            raise ArchivoError(f"no se encontró el archivo '{ruta}'") from None
        except (UnicodeDecodeError, csv.Error) as error:
            raise ArchivoDanadoError(f"no se pudo leer '{ruta}' como CSV de texto: {error}") from None
        except OSError as error:
            raise ArchivoError(f"no se pudo abrir '{ruta}': {error.strerror or error}") from None

    def _validar_renglon(self, valores):
        """Valida todos los campos de un renglón y reporta todos los problemas juntos."""
        if valores is None:
            raise RenglonInvalidoError(f"el renglón no tiene los {len(COLUMNAS)} campos esperados")
        errores = []
        titulo = valores["pelicula"].strip()
        clasificacion = valores["clasificacion"].strip().upper()
        if not titulo:
            errores.append("la película no tiene título")
        if clasificacion not in CLASIFICACIONES:
            errores.append(f"clasificación '{valores['clasificacion'].strip()}' no válida (use A, B o C)")

        duracion = None
        texto = valores["duracion"].strip()
        if re.fullmatch(r"\d+", texto) and 1 <= int(texto) <= 600:
            duracion = int(texto)
        else:
            errores.append(f"duración '{texto}' no válida (use minutos enteros entre 1 y 600)")

        sala = None
        texto = valores["sala"].strip()
        if re.fullmatch(r"\d+", texto) and int(texto) in self._salas:
            sala = int(texto)
        else:
            errores.append(
                f"la sala '{texto}' no existe (salas disponibles: {min(self._salas)} a {max(self._salas)})"
            )

        fecha = hora = None
        try:
            fecha = parsear_fecha(valores["fecha"])
        except DatoInvalidoError as error:
            errores.append(str(error))
        try:
            hora = parsear_hora(valores["hora"])
        except DatoInvalidoError as error:
            errores.append(str(error))

        if errores:
            raise RenglonInvalidoError("; ".join(errores))
        return Pelicula(titulo, clasificacion, duracion), sala, datetime.combine(fecha, hora)
