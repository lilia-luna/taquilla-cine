# Taquilla de un cine

**Tema 1 – Taquilla de un cine** · Proyecto final de Programación Orientada a Objetos (Python)

**Integrantes:**

| Nombre | Cuenta de GitHub/GitLab |
|---|---|
| Luna Delgado Lilia Jimena | @lilia-luna |
| _[Integrante 2]_ | _@usuario2_ |
| _[Integrante 3]_ | _@usuario3_ |
| _[Integrante 4]_ | _@usuario3_ |

Sistema de terminal para vender boletos de un cine de cuatro salas (tradicional, 3D y VIP): carga la
cartelera semanal desde un CSV validando cada renglón, muestra funciones y mapas de asientos, vende
boletos con tarifas, cancela con reembolso, genera reportes diarios, conserva todo entre ejecuciones y
simula la venta concurrente de un estreno (4 taquillas + venta en línea).

## 1. Requisitos e instalación

- **Python 3.10 o superior** (probado con 3.12 y 3.13). **No usa paquetes externos**, solo la biblioteca
  estándar, por eso no hay `requirements.txt`.

```bash
git clone https://github.com/USUARIO/taquilla-cine.git     # cambie la URL por la de su repositorio
cd taquilla-cine
python -m venv .venv                                        # opcional pero recomendado
source .venv/bin/activate                                   # Windows: .venv\Scripts\activate
python -m taquilla_cine --help                              # verifica que funciona
```

Opcional: `pip install -e .` crea además el comando `taquilla` (equivale a `python -m taquilla_cine`).
En macOS/Linux puede ser `python3` en lugar de `python`.

## 2. Cómo ejecutarlo

Hay **dos formas de uso**, que hacen exactamente lo mismo:

- **Comandos** (argparse): `python -m taquilla_cine <comando> ...` — ver `--help` de cada comando.
- **Menú de texto**: `python -m taquilla_cine menu` (o sin ningún comando).

| Comando | Qué hace |
|---|---|
| `cargar ARCHIVO.csv` | Carga la cartelera e informa cada renglón rechazado y su motivo |
| `funciones [--fecha F] [--todas]` | Funciones de un día |
| `mapa ID` | Mapa de asientos (`[ ]` libre, `[X]` ocupado) |
| `vender ID ASIENTO[:TARIFA] ...` | Vende uno o varios asientos y crea el boleto `.txt` |
| `cancelar FOLIO` | Cancela hasta 30 min antes y muestra el reembolso |
| `reporte [--fecha F] [--salida RUTA]` | Reporte del día en un archivo |
| `simular --fecha F [--pelicula T] [--compradores N] [--semilla S] [--sin-guardar]` | Estreno con 5 hilos |
| `menu` | Menú interactivo |

Opciones globales (antes o después del comando):

- `--datos DIR`: carpeta donde se guarda el estado (por omisión `estado/`, que git ignora).
- `--ahora "AAAA-MM-DD HH:MM"`: **fecha y hora de la operación**. Permite probar las reglas que dependen del
  tiempo (tarifa estudiante, cancelación a 30 minutos, venta cerrada) sin esperar. Sin esta opción se usa el reloj.

Tarifas: `general`, `estudiante`, `adulto_mayor`, `nino` (también `niño`). Si se omite, es `general`.
Asientos: fila y número, por ejemplo `A1`, `B7`.

## 3. Cómo probar cada función (con los datos de ejemplo)

Ejecute en orden desde la raíz del repositorio. Para empezar de cero borre la carpeta `estado/`.
Todos los ejemplos fijan `--ahora` para que den siempre el mismo resultado. Los identificadores de función
(F013, F024...) se asignan en el orden del CSV; `funciones --fecha ...` los muestra.

### 3.1 Cargar la cartelera (función 1)

```bash
python -m taquilla_cine cargar datos/cartelera_semana1.csv
# -> 48 funciones aceptadas, 0 renglones rechazados.

python -m taquilla_cine cargar datos/cartelera_con_errores.csv
# -> 3 funciones aceptadas, 11 renglones rechazados (cada uno con su motivo):
#    sala inexistente, fechas y hora inválidas, traslape, falta de limpieza (20 min),
#    clasificación, duración, renglón incompleto, título vacío, choque con la cartelera ya cargada.

python -m taquilla_cine cargar datos/cartelera_danada.csv     # CSV con encabezado incorrecto -> "Error: ..." y sigue vivo
python -m taquilla_cine cargar datos/no_existe.csv            # archivo faltante               -> "Error: no se encontró ..."
```

### 3.2 Ver funciones y mapa (función 2)

```bash
python -m taquilla_cine --ahora "2026-11-26 12:00" funciones --fecha 2026-11-27
python -m taquilla_cine --ahora "2026-11-26 12:00" mapa F013
```

### 3.3 Vender (función 3)

```bash
# Cuatro asientos, cada uno con su tarifa (F013: viernes 14:00, sala 1 tradicional, base $80)
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 A1:general A2:estudiante A3:adulto_mayor B1:nino
# -> FOL-000001 $80.00 | FOL-000002 $56.00 | FOL-000003 $40.00 | FOL-000004 $48.00 | Total $224.00
# -> los boletos quedan en estado/boletos/FOL-00000X.txt
```

Casos que el sistema **debe rechazar** (cada uno muestra `Error: ...` y no vende nada):

```bash
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 A1:general          # asiento ocupado
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 B2 A1               # uno libre y uno ocupado: no vende ninguno
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 Z99                 # asiento inexistente
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 C1 C1               # asiento repetido en la solicitud
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F013 C1:vip              # tarifa que no existe
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F024 A1:nino             # niño en sala VIP
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F016 A1:nino             # niño en película clasificación C
python -m taquilla_cine --ahora "2026-11-26 12:00" vender F026 A1:estudiante       # estudiante en sábado
python -m taquilla_cine --ahora "2026-11-27 14:00" vender F013 D1                  # la función ya comenzó
```

Precios para comprobar: sala 3D (F021) general **$110**; sala VIP (F024) general **$160** y adulto mayor **$80**;
estudiante entre semana en sala 1 = **$56**.

### 3.4 Cancelar (función 4)

```bash
python -m taquilla_cine --ahora "2026-11-27 13:30" cancelar FOL-000002   # exactamente 30 min antes: OK, reembolso $56.00
python -m taquilla_cine --ahora "2026-11-27 13:31" cancelar FOL-000003   # 29 min antes: rechazado
python -m taquilla_cine --ahora "2026-11-27 13:30" cancelar FOL-000002   # ya cancelado: rechazado
python -m taquilla_cine cancelar FOL-999999                              # folio inexistente
python -m taquilla_cine mapa F013                                        # el asiento A2 volvió a quedar libre
```

El archivo `estado/boletos/FOL-000002.txt` queda marcado como CANCELADO con el reembolso.

### 3.5 Reporte del día (función 5)

```bash
python -m taquilla_cine --ahora "2026-11-27 12:00" reporte --fecha 2026-11-27
# -> estado/reportes/reporte_2026-11-27.txt: boletos e ingresos por película y por sala,
#    cancelaciones y % de ocupación de cada función.
```

### 3.6 Conservar datos entre ejecuciones (función 6)

Cada comando es una ejecución distinta del programa y ve lo anterior: el `mapa F013` del paso 3.4 muestra las
ventas hechas en el 3.3. El estado vive en `estado/cartelera.json` y `estado/ventas.json`. Los folios
continúan (el siguiente boleto será `FOL-000005`) y nunca se repiten.

### 3.7 Simular el estreno (función 7)

```bash
python -m taquilla_cine --datos estado_prueba cargar datos/cartelera_semana1.csv
python -m taquilla_cine --datos estado_prueba --ahora "2026-11-26 12:00" simular \
       --fecha 2026-11-27 --pelicula "Galaxia Perdida" --semilla 42
```

Cinco hilos (Taquilla 1 a 4 y Venta en línea) atienden 300 compradores al azar (1 a 4 asientos de una misma
función). Al terminar se imprime el resumen, los "choques" entre hilos que se resolvieron con reintento y la
**verificación**: *ningún asiento se vendió dos veces y los totales coinciden con los mapas de asientos*.
Use `--sin-guardar` para no conservar las ventas simuladas. Después puede ejecutar `reporte --fecha 2026-11-27`
para ver la ocupación. (El número exacto de ventas varía entre corridas porque los hilos compiten; la
verificación debe salir siempre correcta.)

### 3.8 Archivos dañados o faltantes

```bash
cp -r datos/estado_corrupto estado_prueba2         # Windows: xcopy /E /I datos\estado_corrupto estado_prueba2
python -m taquilla_cine --datos estado_prueba2 funciones --todas
# -> "Aviso: ventas.json está dañado ... se conservó como ventas.json.corrupto" y
#    "Aviso: cartelera.json: se omitió la función F002 (la sala 9 no existe)"; el programa continúa con F001.
python -m taquilla_cine --ahora "mañana" funciones           # argumento inválido -> mensaje claro, sin traceback
python -m taquilla_cine funciones --fecha 2026-02-30         # fecha inexistente
```

### 3.9 Menú de texto

```bash
python -m taquilla_cine menu
```

Opciones 1–7 equivalen a los comandos; la 8 cambia la fecha y hora de las operaciones (como `--ahora`).
Las entradas inválidas muestran el error y regresan al menú. `Ctrl+C`/`Ctrl+D` terminan de forma ordenada.

### 3.10 Pruebas automáticas

```bash
python -m unittest discover -s tests -t .          # 41 pruebas; también: python -m unittest -v
```

Cubren precios y tarifas, validación del CSV de ejemplo (renglón por renglón), venta y cancelación con los
límites de tiempo, reporte, persistencia con archivos dañados, 30 hilos disputando un asiento, la simulación
completa y el CLI/menú de extremo a extremo.

## 4. Estructura del proyecto

```
taquilla-cine/
├── README.md                  este archivo
├── pyproject.toml             metadatos (permite pip install -e .); sin dependencias
├── .gitignore                 excluye __pycache__/, .venv/ y estado/ (lo que genera el programa)
├── datos/                     datos de ejemplo (ver datos/README.md): CSV válido, con errores, dañado y estado dañado
├── docs/
│   ├── diseno.md              documento de diseño (UML, decisiones, alternativas, IA, contribuciones)
│   └── uml/                   diagramas PNG y generar_uml.py (los genera a partir del código)
├── tests/                     pruebas automáticas (unittest)
└── taquilla_cine/             paquete principal
    ├── main.py, __main__.py   punto de entrada
    ├── excepciones.py         jerarquía de excepciones propias (base: TaquillaError)
    ├── utilidades.py          fechas, horas y dinero
    ├── dominio/               modelo: Sala (abstracta) y sus tipos, Tarifa (abstracta) y sus tipos,
    │                          Pelicula, Funcion (mapa de asientos protegido con candado), Boleto
    ├── servicios/             Cartelera (carga CSV), Taquilla (vender/cancelar thread-safe),
    │                          ImpresorBoletos, Reportes, SimuladorEstreno (hilos)
    ├── persistencia/          RepositorioJSON: guarda/recupera cartelera y ventas de forma atómica
    └── interfaz/              Aplicacion (casos de uso), cli.py (argparse), menu.py, formato.py
```

Las capas dependen solo de las de abajo: `interfaz → servicios/persistencia → dominio`. Más detalle y
diagramas en [`docs/diseno.md`](docs/diseno.md).

## 5. Decisiones sobre detalles no definidos en el enunciado

Resumen (justificación completa en `docs/diseno.md`): un boleto = un asiento = un folio (`FOL-000001`);
la venta de varios asientos es *todo o nada*; la tarifa de estudiante se valida con el día **de la función**;
el reembolso es el 100 % de lo pagado y la cancelación vale hasta *exactamente* 30 minutos antes; no se
vende una función ya iniciada; el reporte de un día se calcula por la fecha de la función; las salas
(1: tradicional 8×10, 2: tradicional 6×12, 3: 3D 6×10, 4: VIP 4×6) están definidas en `dominio/salas.py`.
