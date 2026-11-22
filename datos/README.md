# Datos de ejemplo

| Archivo | Para qué sirve |
|---|---|
| `cartelera_semana1.csv` | Cartelera **válida** de la semana del 23 al 29 de noviembre de 2026 (48 funciones, sin errores). El viernes 27 es el estreno de *Galaxia Perdida*. Incluye salas tradicionales, 3D y VIP, y películas de clasificación A, B y C. |
| `cartelera_con_errores.csv` | 14 renglones con **un error de cada tipo**: sala inexistente, fecha inválida (dos formas), hora inválida, traslape, falta de los 20 minutos de limpieza, clasificación inválida, duración inválida, renglón incompleto, título vacío y choque con una función ya cargada. Acepta 3 y rechaza 11 (si se carga después de `cartelera_semana1.csv`). |
| `cartelera_danada.csv` | Archivo con encabezado incorrecto: debe rechazarse completo con un mensaje claro. |
| `estado_corrupto/` | Carpeta de estado guardado **dañado** (`ventas.json` truncado y una función con sala inexistente en `cartelera.json`) para probar que el programa no se cae. **Cópiela antes de usarla** (el programa aparta el archivo dañado): ver README principal. |

## Formato del CSV de cartelera

```
pelicula,clasificacion,duracion,sala,fecha,hora
Galaxia Perdida,B,120,1,2026-11-27,14:00
```

- `clasificacion`: A, B o C. `duracion`: minutos enteros (1 a 600).
- `sala`: 1 a 4. `fecha`: `AAAA-MM-DD`. `hora`: `HH:MM` (24 h).
- Entre dos funciones de la misma sala debe haber al menos 20 minutos después de que termina la primera.
