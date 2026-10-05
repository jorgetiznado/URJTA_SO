# NyR con Danna

Danna es quien más sabe de NyR. Esta guía tiene dos partes: **cómo Claude mira NyR** cuando ella
pide ayuda, y **lo que Danna le enseña** (para que no se pierda entre sesiones). Claude la lee cada
vez que el tema es NyR.

---

## 1. Cómo mirar NyR (de lo más rápido a lo más lento)

### a) Lo que ya está en disco: leer primero esto

NyR se baja solo varias veces al día. Casi siempre la respuesta ya está aquí, sin tocar NyR:

| Archivo (en `C:\BD\Drive\SGC\NyR\`) | Qué trae | Se actualiza |
|---|---|---|
| `bandeja_nyr.csv` | Lo **abierto hoy**: sin asignar, asignado, liberado, cargado en PDA (60 días) | cada 30 min, 07–21, lun–sáb |
| `bandeja_nyr_desde.json` | Desde cuándo está cada orden en su estado y con su operador | igual que la bandeja |
| `ordenes_nyr_AAAAMM.csv` | Todas las órdenes del mes (Asignación OT, grilla + Excel) | de madrugada |
| `Cortes en proceso AAAAMM.CSV`, `Cortes históricos …`, `Repos en proceso …` | Los resultados (Informe de Cortes y Reposiciones) | varias veces al día |
| `proceso_ordenes_AAAAMM.csv` | Tipo de proceso: NORMAL, ESPECIAL, VISITA CORTE | de noche |
| `operadores_nyr.csv` | Código y nombre de cada operador como los tiene NyR | con cada bajada |
| `cierres_log\ordenes_equivocadas.csv` | Un caso por línea de orden mal ingresada | con cada diagnóstico |

Y el consolidado de todo: `C:\BD\SGC\Salidas\seguimiento.parquet`.

**Solo se leen.** Nada de abrirlos en Excel y guardar: un archivo bloqueado o cambiado rompe el
pipeline.

### b) Consultar NyR fresco con los scripts de solo lectura

Están en `C:\BD\Drive\TI\Urjta-Cobranza\scrapers`. Ojo: aunque **no cambian NyR**, algunos
**sobrescriben archivos de producción** si no se les da otra carpeta. Por eso, con Danna, siempre
con destino en `danna/datos/nyr/` (no se sube a git):

| Para ver… | Comando |
|---|---|
| Resultados de un día | `python resultados_nyr.py --desde DD-MM-AAAA --hasta DD-MM-AAAA --destino C:\Danna\URJTA_SO\danna\datos\nyr` |
| Órdenes de un rango | `python ordenes_nyr.py --desde DD-MM-AAAA --hasta DD-MM-AAAA --salida-dir C:\Danna\URJTA_SO\danna\datos\nyr` |
| Fotos de una orden | `python fotos_visor.py --servicio <servicio> --orden <orden> --destino C:\Danna\URJTA_SO\danna\datos\nyr\fotos` |
| Orden mal ingresada | la habilidad `nyr-orden-equivocada` (con `--destino` en `danna\datos\nyr\`) |

- `resultados_nyr.py` **sin `--destino`** reemplaza los CSV del mes que lee el pipeline. Nunca.
- `bandeja_nyr.py` no se corre: lo hace la tarea cada 30 min. Se lee `bandeja_nyr.csv`.
- **Estos sí cambian NyR y no se usan** en las sesiones de Danna: `asignar_operador`,
  `reasignar_lote`, `reasignar_masivo`, `cerrar_lote`, `vaciar_pda`,
  `importar_resultados`, `Programa Cierre`. La única excepción es `cerrar_orden.py` dentro de la
  habilidad de orden equivocada, y el guardado lo corre Danna en su terminal.
- Los scripts sacan la clave de `automatizacion\config_*.json`. Esos archivos **no se abren**
  (contraseñas, igual que `.env`).
- NyR es lento: una consulta puede tardar 1–2 minutos. Avísale antes.

### c) Lo que Danna muestra

- **Capturas** (NyR, WhatsApp, formularios): las pega en el chat. Claude las lee.
- **Archivos** (Excel, fotos, PDF): los deja en `danna/datos/casos/AAAA-MM-DD_tema/` y le dice a
  Claude la carpeta.
- **En vivo**: puede abrir NyR en el navegador y mostrárselo a Claude. **Ella inicia sesión, Claude
  nunca escribe la clave.**

---

## 2. Lo que Danna enseña de NyR

Cuando Danna explica cómo funciona algo (una pantalla, un estado, un código, un truco, un error
típico de los operadores), Claude lo anota aquí **con sus palabras** y le pregunta si quedó bien.
Sin datos de clientes. Si algo de aquí contradice el código o los datos, se conversa con ella: puede
que el sistema esté mal, no ella.

### Pantallas

_(vacío: lo llena Danna)_

### Estados y códigos

_(vacío)_

### Trucos y errores típicos

_(vacío)_
