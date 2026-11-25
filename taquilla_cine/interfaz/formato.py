"""Presentación en texto: lista de funciones, mapa de asientos y resultados."""

from ..dominio.funcion import Funcion
from ..servicios.simulador import ResultadoSimulacion
from ..utilidades import dinero, nombre_dia


def encabezado_funcion(funcion: Funcion) -> str:
    """Una línea que describe la función."""
    return (f"{funcion.id} | {funcion.pelicula.titulo} ({funcion.pelicula.clasificacion}, "
            f"{funcion.pelicula.duracion} min) | {funcion.sala} | "
            f"{nombre_dia(funcion.inicio.date())} {funcion.inicio:%Y-%m-%d} {funcion.inicio:%H:%M}-{funcion.fin:%H:%M}")


def lista_de_funciones(funciones: list) -> str:
    """Tabla de funciones."""
    lineas = [f"{'Id':<6}{'Hora':<7}{'Pelicula':<24}{'Clas.':<7}{'Sala':<22}{'Libres':>8}"]
    for f in funciones:
        libres = f.sala.capacidad - f.cantidad_ocupados()
        lineas.append(f"{f.id:<6}{f.inicio:%H:%M}  {f.pelicula.titulo:<24}{f.pelicula.clasificacion:<7}"
                      f"{str(f.sala):<22}{f'{libres}/{f.sala.capacidad}':>8}")
    return "\n".join(lineas)


def mapa_de_asientos(funcion: Funcion) -> str:
    """Mapa con ``[ ]`` para asientos libres y ``[X]`` para ocupados."""
    ocupados = funcion.asientos_ocupados()
    sala = funcion.sala
    ancho = sala.asientos_por_fila * 4 + 2
    lineas = [encabezado_funcion(funcion), "", "PANTALLA".center(ancho).rstrip(), "-" * ancho]
    lineas.append("   " + "".join(f"{n:^4}" for n in range(1, sala.asientos_por_fila + 1)).rstrip())
    for fila in sala.etiquetas_filas():
        celdas = "".join(f"[{'X' if f'{fila}{n}' in ocupados else ' '}] " for n in range(1, sala.asientos_por_fila + 1))
        lineas.append(f"{fila}  {celdas}".rstrip())
    libres = sala.capacidad - len(ocupados)
    lineas += ["", f"Libres: {libres}  Ocupados: {len(ocupados)}  Total: {sala.capacidad}  "
                   f"Precio base: {dinero(sala.precio_base)}"]
    return "\n".join(lineas)


def resumen_simulacion(r: ResultadoSimulacion) -> str:
    """Texto con el resultado de la simulación."""
    lineas = [
        f"Compradores atendidos: {r.compradores} en {r.segundos:.2f} s",
        f"  Con venta:                       {r.ventas}",
        f"  Sin lugar suficiente:            {r.sin_lugar}",
        f"  Abandonaron tras reintentos:     {r.abandonos}",
        f"  Choques por asiento disputado:   {r.conflictos} (se resolvieron con reintento)",
        f"Boletos vendidos: {r.boletos}   Ingresos: {dinero(r.ingresos)}",
        "Por punto de venta (ventas / boletos):",
    ]
    lineas += [f"  {p:<16}{v:>4} / {b:<4}" for p, (v, b) in r.por_punto.items()]
    if r.errores:
        lineas.append(f"Compras rechazadas por reglas ({len(r.errores)}), por ejemplo: {r.errores[0]}")
    if r.correcta:
        lineas.append("VERIFICACION: correcta. Ningun asiento se vendio dos veces y los totales "
                      "coinciden con los mapas de asientos.")
    else:
        lineas.append("VERIFICACION: se detectaron problemas:")
        lineas += [f"  - {p}" for p in r.problemas]
    return "\n".join(lineas)
