# Diseño — Admin como sistema web (MVP Cobranza)

**Fecha:** 2026-07-17
**Estado:** Entrevista cerrada — listo para construir

---

## 1. Visión confirmada

El panel `/admin` deja de ser un hub de módulos aislados y pasa a ser un **sistema web de escritorio único** — en palabras de Jorge, un "ERP personalizado". No son módulos que se construyen y se olvidan uno por uno: **Cobranza es la capa que consolida datos de los demás módulos** (Caja Chica como costo, EEPP como ingreso, terreno como actividad operativa), no un módulo más en la fila.

## 2. Cobranza tiene dos niveles, no uno

Corrigiendo mi supuesto inicial (que Cobranza = solo deuda del cliente final):

| Nivel | Qué muestra | Para quién | Fuente de datos |
|---|---|---|---|
| **Operativo** | Deuda de clientes finales, pagado/pendiente por localidad — lo que ya mockeé | Uso diario, más operativo | `clientes.csv` (columna PAGO) |
| **EERR (Estado de Resultados)** | Ingresos (EEPP) − Costos (Caja Chica) = Resultado | **Esto es lo importante para gerencia** | EEPP vía pipeline (`eepp_final.csv`) + Caja Chica (ya trackeado) |

**Datos EEPP confirmados** (histórico completo): $1.234.549.300 en 144.478 órdenes — CyR $920M, Gestión $161M, Visita $109M, Volante $43M.

**Brecha real detectada:** Combustible (solo litros) y Materiales (solo cantidad) **no tienen costo en pesos hoy** — no pueden entrar al EERR todavía. Decisión: construir el EERR ahora con lo que existe (EEPP − Caja Chica) y sumar Combustible/Materiales cuando tengan un campo de precio.

## 3. Alcance de contrato

Existen 4 líneas de negocio en `operadores.csv` (CYR, FRAUDES, MEDIDORES, OTROS), pero solo **CyR (Corte y Repo)** tiene datos operativos fluyendo hoy. Decisión: diseñar la estructura de datos y UI **pensando en multi-contrato desde ahora** (ej. un selector de contrato, un campo CONTRATO en los modelos), pero el contenido real del MVP cubre solo CyR.

## 4. Modelo de permisos — cambia de fondo

- **La clave única compartida de `/admin` (`urjta2026`) desaparece por completo.** Todo el acceso administrativo pasa al login por rol que ya existe para la app de terreno (Operador / Administrativo-Supervisor / Administrador de Contrato / Dirección-Gerencia).
- **EERR** visible solo para **Dirección/Gerencia + Administrador de Contrato**.
- **Aprobación de Caja Chica**: Dirección/Gerencia, **más José Muñoz específicamente** (código 1, hoy con cargo Administrador de Contrato) — su autoridad de aprobación no depende de un nivel jerárquico general, es una función específica suya. Esto no encaja en el modelo de cargos genérico actual.

  **Propuesta técnica**: agregar una columna nueva `APRUEBA_CAJA_CHICA` (Sí/No) en `operadores.csv`, independiente del CARGO — así cualquier persona puntual (José, o quien tome ese rol después) se marca como aprobador sin tener que inventarle un cargo especial ni hardcodear su nombre en el código.

## 5. Pendiente de construir en `sync_pipeline.py`

Hoy solo trae pendientes de corte (`clientes.csv`). Falta agregar una función que traiga EEPP desde `eepp_final.csv` (por período, por familia) para alimentar el EERR.

## 6. Jerarquía real (corregida 2026-07-17)

- **Mauricio Mollo** (código 5) — dueño → cargo `DIRECCION`
- **Camila Tirado** (código 4) — gerenta → cargo `GERENCIA`
- **Jorge Tiznado** (código 3) — cargo `GERENCIA` por ahora, para probar las funciones

`operadores.csv` ya actualizado con estos tres cargos.

## 7. Para qué sirve el EERR (confirmado)

Todas las hipótesis se confirmaron, más una:
- Rentabilidad mes a mes del contrato con ADA
- Dotación de cuadrillas — **¿falta o sobra gente?**, decisión basada en margen
- Negociación de condiciones con ADA
- **Estado de la facturación** (cómo va cobrado/por cobrar)

La vista debe soportar comparación mes a mes como mínimo (no solo una foto del período actual).

## 8. Reporte externo — no hay obligación, pero hay ángulo estratégico

Hoy **URJTA no le envía reportes a ADA — es al revés** (ADA envía sus análisis a URJTA). Jorge califica esos análisis de ADA como "mediocres". Este sistema es en primer lugar **de uso interno**, pero con un objetivo estratégico explícito: **demostrar valor** — implica que en algún momento podría mostrarse a ADA como evidencia de una gestión más sofisticada que la de ellos. No es un reporte periódico obligatorio; es una vitrina posible, no un requisito de formato/fecha externo.

## 9. Combustible — el costo SÍ es capturable

El combustible funciona por **vale**: el Administrador de Contrato define un monto, el operador va a la bencinera y le cargan hasta ese valor. O sea **el monto es conocido de antemano, no varía de forma impredecible por factura** — no es una brecha de "precio de mercado desconocido", es simplemente **un campo que falta agregar al formulario** (`Combustible.html`/`registrar_combustible`), junto a la foto del vale que ya se captura hoy.

**Acción concreta:** agregar campo `MONTO_VALE` a `combustible.csv` y al formulario de registro — con esto, Combustible puede sumarse al EERR sin esperar más brechas de datos.

---

## 10. Plan de construcción — orden de ejecución

Dado el incidente reciente (agregar login obligatorio a Geo bloqueó a terreno en vivo), la migración de `/admin` a login por rol se hace **por etapas, nunca de golpe**:

1. Agregar columna `APRUEBA_CAJA_CHICA` a `operadores.csv` (cambio de datos, sin riesgo)
2. Agregar campo `MONTO_VALE` a Combustible (formulario + CSV)
3. Extender `sync_pipeline.py` para traer EEPP desde `eepp_final.csv`
4. Construir el nuevo login por rol para `/admin` **en paralelo** a la clave única existente (ambas funcionando a la vez), probar a fondo con Jorge/Camila/Mauricio
5. Solo cuando el login por rol esté verificado y estable, recién ahí se retira la clave única compartida
6. Reconstruir Cobranza (operativo + EERR) sobre el esqueleto de escritorio ya mockeado
7. Migrar el resto de los módulos de Admin al mismo esqueleto, según prioridad futura
