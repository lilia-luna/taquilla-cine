"""Genera los diagramas UML de docs/uml a partir del código real.

Los atributos y métodos de cada clase se leen del código (inspect + ast), así
los diagramas no se desactualizan: basta volver a ejecutar

    python docs/uml/generar_uml.py

Requiere Graphviz (comando ``dot``) y matplotlib (solo para el diagrama de secuencia).
"""

import ast
import dataclasses
import inspect
import subprocess
import sys
import textwrap
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from taquilla_cine import excepciones as exc  # noqa: E402
from taquilla_cine.dominio import (Boleto, Funcion, Pelicula, Sala, Sala3D, SalaTradicional, SalaVIP, Tarifa,  # noqa: E402
                                   TarifaAdultoMayor, TarifaEstudiante, TarifaGeneral, TarifaNino)
from taquilla_cine.interfaz.aplicacion import Aplicacion  # noqa: E402
from taquilla_cine.interfaz.menu import Menu  # noqa: E402
from taquilla_cine.persistencia import RepositorioJSON  # noqa: E402
from taquilla_cine.servicios import (Cartelera, ImpresorBoletos, Rechazo, ReporteDia, Reportes,  # noqa: E402
                                     ResultadoCarga, ResultadoSimulacion, SimuladorEstreno, SolicitudAsiento, Taquilla)
from taquilla_cine.servicios.simulador import Comprador  # noqa: E402


def esc(texto):
    for a, b in (("\\", "\\\\"), ("{", "\\{"), ("}", "\\}"), ("|", "\\|"), ("<", "\\<"), (">", "\\>")):
        texto = texto.replace(a, b)
    return texto


def atributos_privados(clase):
    """Atributos ``self._x`` asignados en __init__ (se leen del código fuente)."""
    try:
        arbol = ast.parse(textwrap.dedent(inspect.getsource(clase)))
    except (OSError, TypeError):
        return []
    nombres = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "__init__":
            for sub in ast.walk(nodo):
                objetivos = []
                if isinstance(sub, ast.Assign):
                    objetivos = sub.targets
                elif isinstance(sub, ast.AnnAssign):
                    objetivos = [sub.target]
                planos = []
                for t in objetivos:
                    planos += list(t.elts) if isinstance(t, ast.Tuple) else [t]
                for t in planos:
                    if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"
                            and t.attr.startswith("_") and not t.attr.startswith("__") and t.attr not in nombres):
                        nombres.append(t.attr)
    return nombres


def etiqueta(clase, solo_nombre=False):
    nombre = esc(clase.__name__)
    if inspect.isabstract(clase):
        nombre = "«abstracta»\\n" + nombre
    if solo_nombre:
        return "{" + nombre + "}"
    attrs, metodos = [], []
    if dataclasses.is_dataclass(clase):
        attrs += [f"+ {f.name}" for f in dataclasses.fields(clase)]
    for n in atributos_privados(clase):
        attrs.append(f"- {n[1:]}")
    for n, v in vars(clase).items():
        if n.startswith("_"):
            continue
        if isinstance(v, property):
            attrs.append(f"+ {n}" + (" {solo lectura}" if v.fset is None else ""))
        elif isinstance(v, (staticmethod, classmethod)) or inspect.isfunction(v):
            f = v.__func__ if isinstance(v, (staticmethod, classmethod)) else v
            sufijo = " {abstracto}" if getattr(f, "__isabstractmethod__", False) else ""
            metodos.append(f"+ {n}(){sufijo}")
        elif dataclasses.is_dataclass(clase) and n in {f.name for f in dataclasses.fields(clase)}:
            continue
        elif not callable(v) and isinstance(v, (str, int, float)) or v.__class__.__name__ in ("Decimal", "timedelta"):
            attrs.append(f"+ {n} {{constante}}")
    cuerpo = "|" + "".join(esc(a) + "\\l" for a in attrs) + "|" + "".join(esc(m) + "\\l" for m in metodos)
    return "{" + nombre + cuerpo + "}"


ESTILOS = {
    "herencia": 'arrowhead=empty',
    "composicion": 'arrowhead=diamond',
    "agregacion": 'arrowhead=odiamond',
    "asociacion": 'arrowhead=vee',
    "dependencia": 'arrowhead=vee, style=dashed',
}


def compilar(nombre, texto):
    """Escribe un .dot, lo convierte a PNG con Graphviz y borra el .dot."""
    ruta = SALIDA / f"{nombre}.dot"
    ruta.write_text(texto, encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=110", str(ruta), "-o", str(SALIDA / f"{nombre}.png")], check=True)
    ruta.unlink()


def dot(nombre, titulo, clases, relaciones, sustitutos=(), extras="", rankdir="BT"):
    """Diagrama de clases. ``relaciones``: (origen, destino, tipo, etiqueta)."""
    lineas = [f'digraph "{nombre}" {{', f'  rankdir={rankdir}; labelloc=t; fontsize=18; label="{titulo}";',
              '  node [shape=record, fontname="Helvetica", fontsize=10, style=filled, fillcolor="#fdfdf4"];',
              '  edge [fontname="Helvetica", fontsize=9];']
    for c in clases:
        lineas.append(f'  {c.__name__} [label="{etiqueta(c)}"];')
    for c in sustitutos:
        lineas.append(f'  {c.__name__} [label="{etiqueta(c, True)}", fillcolor="#e8e8e8"];')
    lineas.append(extras)
    for origen, destino, tipo, texto in relaciones:
        atrib = ESTILOS[tipo]
        if tipo == "herencia":
            lineas.append(f'  {origen} -> {destino} [{atrib}];')
        elif tipo in ("composicion", "agregacion"):  # origen = el todo; el rombo va en el todo
            lineas.append(f'  {destino} -> {origen} [{atrib}, label="{texto}"];')
        else:
            lineas.append(f'  {origen} -> {destino} [{atrib}, label="{texto}"];')
    lineas.append("}")
    compilar(nombre, "\n".join(lineas))


def herencias(clases):
    conjunto = set(clases)
    return [(c.__name__, b.__name__, "herencia", "") for c in clases for b in c.__bases__ if b in conjunto]


def diagrama_dominio():
    clases = [Sala, SalaTradicional, Sala3D, SalaVIP, Tarifa, TarifaGeneral, TarifaEstudiante, TarifaAdultoMayor,
              TarifaNino, Pelicula, Funcion, Boleto]
    fabricas = ('  FabricaSalas [shape=note, label="crear_sala()\\ncrear_salas_del_cine()\\n«fábrica»", fillcolor="#ffffcc"];\n'
                '  FabricaTarifas [shape=note, label="obtener_tarifa()\\n«fábrica»", fillcolor="#ffffcc"];')
    rel = herencias(clases) + [
        ("Funcion", "Sala", "agregacion", "sala"),
        ("Funcion", "Pelicula", "agregacion", "pelicula"),
        ("Boleto", "Funcion", "asociacion", "funcion_id"),
        ("Tarifa", "Funcion", "dependencia", "validar(funcion)"),
        ("FabricaSalas", "Sala", "dependencia", "«crea»"),
        ("FabricaTarifas", "Tarifa", "dependencia", "«devuelve»"),
    ]
    dot("clases_dominio", "Diagrama de clases - dominio (salas, tarifas, funciones, boletos)", clases, rel, extras=fabricas)


def diagrama_servicios():
    clases = [Cartelera, ResultadoCarga, Rechazo, Taquilla, SolicitudAsiento, ImpresorBoletos, Reportes, ReporteDia,
              SimuladorEstreno, Comprador, ResultadoSimulacion, RepositorioJSON, Aplicacion, Menu]
    rel = [
        ("Menu", "Aplicacion", "agregacion", "app"),
        ("Aplicacion", "RepositorioJSON", "composicion", "repositorio"),
        ("Aplicacion", "ImpresorBoletos", "composicion", "impresor"),
        ("Aplicacion", "Reportes", "composicion", "reportes"),
        ("Aplicacion", "Cartelera", "composicion", "cartelera"),
        ("Aplicacion", "Taquilla", "composicion", "taquilla"),
        ("Taquilla", "Cartelera", "agregacion", "cartelera"),
        ("Cartelera", "Funcion", "composicion", "1..*"),
        ("Cartelera", "Sala", "agregacion", "4"),
        ("Taquilla", "Boleto", "composicion", "0..*"),
        ("Reportes", "Cartelera", "agregacion", ""),
        ("Reportes", "Taquilla", "agregacion", ""),
        ("SimuladorEstreno", "Taquilla", "agregacion", ""),
        ("ResultadoCarga", "Rechazo", "composicion", "0..*"),
        ("Cartelera", "ResultadoCarga", "dependencia", "cargar_csv()"),
        ("Taquilla", "SolicitudAsiento", "dependencia", "vender()"),
        ("Taquilla", "Tarifa", "dependencia", "validar / precio"),
        ("Reportes", "ReporteDia", "dependencia", "generar()"),
        ("SimuladorEstreno", "Comprador", "dependencia", "5 hilos"),
        ("SimuladorEstreno", "ResultadoSimulacion", "dependencia", "ejecutar()"),
        ("ImpresorBoletos", "Boleto", "dependencia", "escribir()"),
        ("RepositorioJSON", "Cartelera", "dependencia", "guardar / cargar"),
        ("RepositorioJSON", "Taquilla", "dependencia", "guardar / cargar"),
    ]
    dot("clases_servicios", "Diagrama de clases - servicios, persistencia e interfaz", clases, rel,
        sustitutos=[Funcion, Sala, Boleto, Tarifa], rankdir="TB")


def diagrama_excepciones():
    clases = [c for _, c in inspect.getmembers(exc, inspect.isclass) if c.__module__ == exc.__name__]
    clases.sort(key=lambda c: c.__name__)
    dot("excepciones", "Jerarquia de excepciones propias", clases, herencias(clases))


def diagrama_capas():
    compilar("arquitectura", '''digraph arquitectura {
  rankdir=TB; newrank=true; nodesep=0.5; ranksep=0.7; labelloc=t; fontsize=18; label="Arquitectura por capas y archivos";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#eef5ff"];
  edge [fontname="Helvetica", fontsize=9];
  subgraph cluster_ui { label="interfaz/"; style=dashed;
    cli [label="cli.py\\nargparse (comandos)"]; menu [label="menu.py\\nmenu de texto"];
    app [label="aplicacion.py\\nAplicacion"]; fmt [label="formato.py\\nmapa y tablas"]; }
  subgraph cluster_srv { label="servicios/"; style=dashed;
    cart [label="cartelera.py\\nCartelera + CSV"]; taq [label="taquilla.py\\nTaquilla (vender/cancelar)"];
    rep [label="reportes.py"]; imp [label="impresor.py"]; sim [label="simulador.py\\n5 hilos"]; }
  subgraph cluster_dom { label="dominio/"; style=dashed;
    sala [label="salas.py\\nSala (abstracta)"]; tar [label="tarifas.py\\nTarifa (abstracta)"];
    fun [label="funcion.py\\nPelicula, Funcion"]; bol [label="boleto.py\\nBoleto"]; }
  subgraph cluster_per { label="persistencia/"; style=dashed; repo [label="repositorio.py\\nRepositorioJSON"]; }
  exc [label="excepciones.py\\n(todas heredan de TaquillaError)", fillcolor="#fff0f0"];
  csv [shape=cylinder, label="datos/*.csv\\ncartelera semanal", fillcolor="#fffbe0"];
  json [shape=cylinder, label="estado/*.json\\ncartelera y ventas", fillcolor="#fffbe0"];
  txt [shape=cylinder, label="estado/boletos/*.txt\\nestado/reportes/*.txt", fillcolor="#fffbe0"];
  main [label="main.py / __main__.py", fillcolor="#e6ffe6"];
  main -> cli; cli -> app; menu -> app; app -> fmt;
  app -> cart; app -> taq; app -> rep; app -> imp; app -> sim; app -> repo;
  taq -> cart; rep -> cart; rep -> taq; sim -> taq; cart -> fun; cart -> sala; taq -> tar; taq -> bol; taq -> fun;
  tar -> fun [style=dashed]; fun -> sala; imp -> bol; repo -> cart; repo -> taq;
  csv -> cart [label="lee"]; repo -> json [dir=both, label="lee/escribe"]; imp -> txt [label="escribe"]; rep -> txt [label="escribe"];
  exc -> app [style=dotted, arrowhead=none, label="capturada en la interfaz"];
}''')


def diagrama_concurrencia():
    compilar("concurrencia", '''digraph concurrencia {
  rankdir=LR; labelloc=t; fontsize=18; label="Hilos y candados en la venta del estreno";
  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, fillcolor="#eef5ff"];
  edge [fontname="Helvetica", fontsize=9];
  cola [label="queue.Queue\\n300 compradores", shape=cylinder, fillcolor="#fffbe0"];
  subgraph cluster_h { label="5 hilos (SimuladorEstreno)"; style=dashed;
    h1 [label="Taquilla 1"]; h2 [label="Taquilla 2"]; h3 [label="Taquilla 3"]; h4 [label="Taquilla 4"]; h5 [label="Venta en linea"]; }
  vender [label="Taquilla.vender()\\n1) valida fuera del candado\\n2) with funcion.lock:\\n   revisa y ocupa (todo o nada)", fillcolor="#e6ffe6"];
  subgraph cluster_f { label="un RLock por Funcion"; style=dashed; f1 [label="F013.lock"]; f2 [label="F014.lock"]; fn [label="..."]; }
  reg [label="_lock_registro\\nfolios y dict de boletos", fillcolor="#fff0f0"];
  cola -> h1; cola -> h2; cola -> h3; cola -> h4; cola -> h5;
  h1 -> vender; h2 -> vender; h3 -> vender; h4 -> vender; h5 -> vender;
  vender -> f1; vender -> f2; vender -> fn;
  vender -> reg [label="siempre despues\\ndel candado de funcion"];
}''')


def diagrama_estados():
    compilar("estados_boleto", '''digraph estados {
  rankdir=LR; labelloc=t; fontsize=18; label="Diagrama de estados del Boleto";
  node [fontname="Helvetica", fontsize=11]; edge [fontname="Helvetica", fontsize=10];
  inicio [shape=circle, label="", style=filled, fillcolor=black, width=0.25];
  ACTIVO [shape=box, style="rounded,filled", fillcolor="#e6ffe6"];
  CANCELADO [shape=box, style="rounded,filled", fillcolor="#fff0f0"];
  fin [shape=doublecircle, label="", style=filled, fillcolor=black, width=0.2];
  inicio -> ACTIVO [label="Taquilla.vender()\\n[asiento libre, tarifa permitida,\\nfuncion no iniciada]"];
  ACTIVO -> CANCELADO [label="Taquilla.cancelar()\\n[ahora <= inicio - 30 min]\\nreembolso = precio pagado"];
  ACTIVO -> ACTIVO [label="cancelar() fuera de tiempo\\n=> CancelacionNoPermitidaError"];
  CANCELADO -> fin [label="el asiento queda libre;\\nel folio no se reutiliza"];
}''')


def diagrama_secuencia():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    actores = ["Usuario", "cli / menu", "Aplicacion", "Taquilla", "Tarifa", "Funcion", "Repositorio\nJSON", "Impresor\nBoletos"]
    x = {a: i * 2.4 for i, a in enumerate(actores)}
    mensajes = [
        ("Usuario", "cli / menu", "vender F013 A1:estudiante"),
        ("cli / menu", "Aplicacion", "vender(funcion_id, textos)"),
        ("Aplicacion", "Taquilla", "vender(funcion_id, solicitudes, ahora)"),
        ("Taquilla", "Funcion", "sala.normalizar_asiento(A1)"),
        ("Taquilla", "Tarifa", "validar(funcion) / precio(base)"),
        ("Taquilla", "Funcion", "with lock: esta_ocupado(A1)? -> ocupar(A1, folio)"),
        ("Taquilla", "Aplicacion", "boletos (o TaquillaError)"),
        ("Aplicacion", "Repositorio\nJSON", "guardar(cartelera, taquilla)"),
        ("Aplicacion", "Impresor\nBoletos", "escribir(boleto, funcion) -> FOL-000001.txt"),
        ("Aplicacion", "Usuario", "folios, precios y total"),
    ]
    alto = len(mensajes) + 1.5
    fig, ax = plt.subplots(figsize=(17, 7.5))
    ax.set_xlim(-1.3, x[actores[-1]] + 1.6)
    ax.set_ylim(-alto, 1.2)
    ax.axis("off")
    ax.set_title("Diagrama de secuencia: vender boletos", fontsize=16)
    for a in actores:
        ax.text(x[a], 0.55, a, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round", fc="#eef5ff"))
        ax.plot([x[a], x[a]], [0.2, -alto + 0.3], color="gray", ls="--", lw=0.8)
    for i, (o, d, texto) in enumerate(mensajes, start=1):
        y = -i
        retorno = o == "Taquilla" and d == "Aplicacion" or (o == "Aplicacion" and d == "Usuario")
        ax.annotate("", xy=(x[d], y), xytext=(x[o], y),
                    arrowprops=dict(arrowstyle="->", lw=1.3, ls="--" if retorno else "-"))
        ax.text((x[o] + x[d]) / 2, y + 0.12, f"{i}. {texto}", ha="center", va="bottom", fontsize=8.5)
    ax.add_patch(plt.Rectangle((x["Funcion"] - 0.25, -6.45), 0.5, 0.9, fc="#ffe9a8", ec="black", zorder=0))
    ax.text(x["Funcion"] + 0.35, -6.0, "candado de\nla funcion", fontsize=8, va="center")
    fig.tight_layout()
    fig.savefig(SALIDA / "secuencia_venta.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    diagrama_dominio()
    diagrama_servicios()
    diagrama_excepciones()
    diagrama_capas()
    diagrama_concurrencia()
    diagrama_estados()
    diagrama_secuencia()
    print("Diagramas generados en", SALIDA)
