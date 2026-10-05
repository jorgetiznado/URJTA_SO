# Tus dashboards

Cada archivo `.json` de esta carpeta es un dashboard. En internet aparece en la pestaña
**Dashboards** de proyecto.urjta.cl/danna, como un botón más. Se lee en vivo: guardas y recargas.

El archivo dice **qué mirar**; el sistema hace el cálculo y el dibujo con los mismos datos que usa todo
URJTA (lo que ves tú es lo mismo que ve Jorge para esa zona). Si algo queda mal escrito, la pestaña te
dice qué y cómo arreglarlo.

Los números al inicio del nombre (`01-`, `02-`…) solo sirven para ordenarlos.

## Cómo se escribe uno

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

| Campo | Qué es | Valores |
|---|---|---|
| `titulo` | El nombre del botón (máx. 40 letras) | texto |
| `descripcion` | Para qué sirve | texto (opcional) |
| `fuente` | De dónde salen los datos | `abiertas`, `visitas`, `eepp` |
| `ultimos_dias` | Cuántos días hacia atrás (no aplica a `abiertas`) | 1 a 400 (si no lo pones: 30) |
| `filtros` | Quedarse solo con algunos | `{"columna": "valor"}` o `{"columna": ["valor1", "valor2"]}` |
| `agrupar` | Cómo separar | una columna de texto, o `dia`, `semana`, `mes` |
| `medida` | Qué contar | `cantidad`, `suma:<columna>`, `promedio:<columna>` |
| `grafico` | Cómo dibujarlo | `barras`, `columnas`, `tabla`, `cifra` |
| `limite` | Cuántas filas mostrar | 1 a 50 (si no lo pones: 15) |

La zona no va en el archivo: se elige arriba en la página, igual que en las otras pestañas.

## Las fuentes y sus columnas

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

- Reposiciones por operador en la última semana.
- Improcedencias **propias** por operador (`"filtros": {"categoria": "Improcedencia", "responsable": "Propia"}`).
- EE.PP. por mes del último año (`"agrupar": "mes"`, `"ultimos_dias": 365`).
- Deuda promedio de las órdenes sin asignar por localidad (`"medida": "promedio:deuda"`).

Pregunta siempre: ¿este número cuadra con lo que veo en otra pestaña? Si no cuadra, algo está mal
(o descubriste algo).
