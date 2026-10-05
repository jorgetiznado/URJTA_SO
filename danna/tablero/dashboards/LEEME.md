# Tus dashboards

Cada archivo `.json` de esta carpeta es un dashboard. En internet aparece en la pestaña
**Dashboards** de proyecto.urjta.cl/danna, como un botón más. Se lee en vivo: guardas y recargas.

El archivo dice **qué mirar**; el sistema hace el cálculo y el dibujo con los mismos datos que usa todo
URJTA (lo que ves tú es lo mismo que ve Jorge para esa zona). Si algo queda mal escrito, el dashboard
te dice qué y cómo arreglarlo.

Los números al inicio del nombre (`00-`, `01-`…) solo sirven para ordenarlos.

**`00-mi-qv.json` es tu QlikView de siempre**, rehecho aquí: visitas, cortes, reposiciones y escombros
del mes contra el mes anterior. En septiembre 2026 da exactamente los mismos números que el QV. Es tuyo:
puedes quitarle bloques, agregarle otros o cambiar el orden.

## Un dashboard simple (un solo gráfico)

```json
{
  "titulo": "Improcedencias por motivo",
  "descripcion": "Para qué sirve, en una o dos frases.",
  "fuente": "visitas",
  "ultimos_dias": 30,
  "filtros": { "categoria": "Improcedencia" },
  "agrupar": "resultado",
  "medida": "cantidad",
  "grafico": "barras",
  "limite": 12
}
```

## Un dashboard con varios bloques (como el QV)

```json
{
  "titulo": "Mi QV",
  "fuente": "gestion",
  "periodo": "actual",
  "comparar": "mismos_dias",
  "bloques": [
    { "titulo": "Cortes por localidad", "grafico": "comparativo", "filtros": { "tipo": "Corte" },
      "agrupar": ["localidad", "instancia"], "exito": { "columna": "pago", "valor": "Sí", "nombre": "Pago" } },
    { "titulo": "Cortes por día", "grafico": "columnas", "filtros": { "tipo": "Corte" },
      "agrupar": "dia", "limite": 31, "promedio": true }
  ]
}
```

Lo que va arriba (`fuente`, `periodo`, `filtros`, `comparar`, `ultimos_dias`) vale para todos los
bloques; un bloque puede cambiarlo poniendo su propio valor.

## Los campos

| Campo | Qué es | Valores |
|---|---|---|
| `titulo` | El nombre del botón o del bloque | texto |
| `descripcion` | Para qué sirve | texto (opcional) |
| `fuente` | De dónde salen los datos | `gestion`, `abiertas`, `visitas`, `eepp` |
| `periodo` | Usar el mes elegido arriba (con su selector de período) | `"actual"` (o no ponerlo) |
| `ultimos_dias` | Cuántos días hacia atrás, si no usas `periodo` | 1 a 400 (si no lo pones: 30) |
| `filtros` | Quedarse solo con algunos | `{"columna": "valor"}` o `{"columna": ["valor1", "valor2"]}` |
| `agrupar` | Cómo separar | una columna de texto, o `dia`, `semana`, `mes`, `periodo`; en `comparativo` puede ser una lista de dos |
| `medida` | Qué contar | `cantidad`, `suma:<columna>`, `promedio:<columna>` |
| `grafico` | Cómo dibujarlo | `barras`, `columnas`, `tabla`, `cifra`, `comparativo`, `semaforo` |
| `limite` | Cuántas filas o columnas mostrar | 1 a 50 (si no lo pones: 15) |
| `comparar` | Contra qué compara el `comparativo` | `mismos_dias` (recomendado) o `mes_completo` |
| `exito` | Qué cuenta como bueno (pagos, a tiempo…) | `{"columna": "pago", "valor": "Sí", "nombre": "Pagos"}` |
| `meta` | El % para estar bien (semáforo y color del %) | 0 a 100 (si no lo pones: 80) |
| `promedio` | Dibujar la línea del promedio en `columnas` | `true` |
| `ancho` | Que el bloque ocupe todo el ancho | `"completo"` |

La zona no va en el archivo: se elige arriba en la página, igual que en las otras pestañas.

### Los gráficos

- `barras`: una barra por grupo, de mayor a menor.
- `columnas`: una columna por día, semana, mes o período, de izquierda a derecha. La más clara va en curso.
- `tabla`: los mismos números en tabla, con su %.
- `cifra`: solo el total.
- `comparativo`: la tabla del QV, con Ant, Actual, Dif y Var, más el `exito` y su %. Con
  `"agrupar": ["localidad", "instancia"]` arma grupos con subtotales.
- `semaforo`: una luz por grupo; verde si el % de `exito` llega a la `meta`.

### Ojo con "Ant"

Si el mes va en curso y comparas contra el mes anterior **completo**, siempre vas a ver caídas enormes
(por ejemplo −86% con 2 días hábiles contra 21). Por eso `mismos_dias` compara contra los mismos días del
mes anterior. Debajo de cada tabla igual se dice cuánto fue el mes anterior completo.

## Las fuentes y sus columnas

**`gestion`**: las filas del pipeline que usa el QV (desde 2020), por período.
- Texto: `tipo` (Visita, Corte, Reposición, Improcedencia, Repo improcedente, Otro), `localidad`
  (ARICA, IQUIQUE, ALTO HOSPICIO, PAMPA), `localidad_c` (la localidad exacta: HUARA, PICA…), `zona`,
  `instancia` (1° INSTANCIA, 2° INSTANCIA), `tipo_corte` (Simple = llave o retiro, Cañería), `pago` (Sí, No),
  `plazo` (A tiempo = repuesta en menos de 4 h, Retraso), `escombro` (Sí, No), `operador` (M. Rivero…),
  `dia_semana` (Lunes…)
- Números: `deuda`

**`abiertas`**: las órdenes abiertas hoy en NyR (generadas en los últimos 2 meses).
- Texto: `clase` (Corte, Reposicion), `estado` (Sin asignar, Asignada, En PDA), `operador`, `localidad`, `zona`
- Números: `dias` (desde que se generó), `deuda`, `antiguedad` (meses de deuda)

**`visitas`**: cada visita de corte o reposición del pipeline (hasta 400 días atrás).
- Texto: `accion` (Corte, Reposición), `categoria` (Corte, Reposición, Gestión de pago, Visita (volante),
  Improcedencia, Cierre del sistema), `resultado` (Casa cerrada cortable, Cancelado…), `responsable`
  (Propia, Empresa, Técnica), `operador`, `localidad`, `zona`
- Números: `deuda`

**`eepp`**: el EE.PP. por orden (estimación interna a tarifas del contrato).
- Texto: `tipo` (Cortes, Reposiciones, Gestiones de pago, Visitas, Retiros y otros), `operador`, `zona`
- Números: `monto`

## Ideas para empezar

- Cortes por día de la semana en el mes (`"agrupar": "dia_semana"`).
- Improcedencias **propias** por operador (`"filtros": {"categoria": "Improcedencia", "responsable": "Propia"}`).
- Un semáforo de pago de los cortes por localidad (`exito` pago = Sí, `meta` 60).
- Deuda promedio de las órdenes sin asignar por localidad (`"medida": "promedio:deuda"`).

Pregunta siempre: ¿este número cuadra con lo que veo en otra pestaña? Si no cuadra, algo está mal
(o descubriste algo).
