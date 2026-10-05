# Bitácora de Danna

Cada sesión deja una entrada aquí, la más nueva arriba. Es el registro de qué se hizo, qué se
aprendió y cómo volver atrás si hace falta.

Formato de cada entrada:

```
## AAAA-MM-DD — título corto
**Quería:** lo que Danna pidió, con sus palabras.
**Hicimos:** qué cambió, en simple.
**Aprendí:** conceptos nuevos (contrato o IA).
**Commits:** hash — mensaje
**Para la próxima:** idea o misión siguiente.
**Ideas para Jorge:** (si surgió algo que toca el sistema real)
```

Un punto de guardado se anota así: `PUNTO DE GUARDADO — <hash> — antes de <qué cambio grande>`.

---

## 2026-10-05 — Las sesiones de Danna son clones de las de Jorge
**Quería:** (sesión de Jorge) que Danna trabaje en sesiones como esta, con la misma configuración.
**Hicimos:** `CLAUDE.md` → "Quién está en la sesión": la cuenta dice Jorge pero por defecto está
Danna; Jorge se identifica, y sus commits van con `git -c user.name=Jorge`. Las herramientas de
Jorge que no están autorizadas para ella quedan nombradas. Lo mismo quedó en la memoria de Claude
para esta carpeta. Pendiente: confirmar en una sesión nueva que Claude carga las habilidades de
`danna/.claude/skills/` (prueba: `/prueba-danna`, después se borra).
**Aprendí:** —
**Commits:** este (`danna: las sesiones de Danna son clones de las de Jorge`).

## 2026-10-05 — Claude aprende NyR de Danna
**Quería:** (sesión de Jorge) que Danna pueda pedir ayuda para ver cosas de NyR, traer casos
manuales y que Claude aprenda de ella, "la más experta en NyR", hasta crear habilidades nuevas.
**Hicimos:** `NYR.md`: cómo mirar NyR (primero lo que ya está en disco, después los scripts de
solo lectura con destino en `danna/datos/nyr/`, y qué scripts nunca usar) y una sección "Lo que
Danna enseña". `CASOS.md`: registro de casos sin datos de clientes; el detalle va a
`danna/datos/casos/`. `CLAUDE.md` sección 7: en NyR la experta es ella, y cómo se crean sus
habilidades en `danna/.claude/skills/`. El `.gitignore` del repo ahora versiona esas habilidades
(el resto de `.claude/` sigue fuera). "Habilidad (skill)" en el glosario.
**Aprendí:** —
**Commits:** este (`danna: Claude aprende NyR de Danna, casos y habilidades propias`).
**Para la próxima:** que Danna traiga su primer caso de NyR y le enseñe a Claude una pantalla.

## 2026-10-05 — Más herramientas: Drive, correcciones en NyR y commits propios
**Quería:** (sesión de Jorge) que Danna tenga todas las herramientas para crecer: "confío en ella".
**Hicimos:** **AUTORIZACIÓN DE JORGE:** Danna puede usar el conector de **Google Drive** y **corregir
órdenes mal ingresadas en NyR** con la skill `nyr-orden-equivocada`, siempre confirmando ella antes
de guardar. Notion, Gmail y Canva siguen sin autorizar. Reglas actualizadas en `CLAUDE.md`
(sección 4). Desde ahora los commits de este clon salen a nombre de **Danna**. Se ponen al día las
tres entradas de abajo que faltaban.
**Aprendí:** —
**Commits:** este (`danna: autoriza Drive y correcciones en NyR, bitacora al dia`).
**Para la próxima:** primera sesión de Danna.

## 2026-10-05 — Mi QV como dashboard editable
**Quería:** (sesión de Jorge) tener el QlikView de siempre dentro del sistema, y que Danna pueda
cambiarlo.
**Hicimos:** dashboard `00-mi-qv.json`: visitas, cortes, reposiciones y escombros del mes contra el
mes anterior. La guía `dashboards/LEEME.md` ahora explica los bloques con que se arma un dashboard.
**Aprendí:** —
**Commits:** 676c856 — danna: Mi QV como dashboard editable y guia de bloques

## 2026-10-05 — Dashboards propios
**Quería:** (sesión de Jorge) que Danna pueda armar sus propios dashboards sin tocar el sistema.
**Hicimos:** pestaña Dashboards: cada archivo en `tablero/dashboards/` es un botón. Siete de base
(abiertas por operador, deuda sin asignar, trabajo por día, resultados del mes, improcedencias por
motivo, cortes por operador, EE.PP. por semana) y su guía `LEEME.md`.
**Aprendí:** —
**Commits:** d549165 — danna: dashboards propios, 7 de base y su guia

## 2026-10-05 — El foco en las órdenes
**Quería:** (sesión de Jorge) que el tablero muestre primero las órdenes, no solo el EE.PP.
**Hicimos:** pestañas de órdenes abiertas hoy en NyR por zona, urgencias, quién tiene qué,
repitencias y un buscador con el historial de cada servicio. Quedó en "Lo construido".
**Aprendí:** —
**Commits:** b3788da — danna: el tablero pone el foco en las ordenes

## 2026-10-05 — El tablero sale a internet, mes a mes
**Quería:** (sesión de Jorge) que el tablero viva dentro del sistema para abrirlo desde internet, con
filtros por período, porque el EE.PP. acumulado engaña.
**Hicimos:** página **proyecto.urjta.cl/danna** dentro de la app (la ven Danna, Dirección y Gerencia).
Muestra el EE.PP. de un mes a la vez, con filtro de período y zona: lo facturado, la comparación con
los mismos días del mes anterior, el cierre proyectado, el detalle por tipo de trabajo y los últimos
13 meses (cada mes por separado). Avisa que desde el 01-10 ADA solo genera cortes desde ~$50 mil.
El tablero se separó en `contenido.js` (texto, en JSON), `estilo.css` (diseño) e `index.html`
(vista local); la app lee los dos primeros en vivo desde esta carpeta. Danna entró al equipo de
confianza (ve montos del EE.PP. en todo el sistema).
**Aprendí:** —
**Commits:** este (`danna: tablero en internet con el EE.PP. por período`); en el sistema, a790181.
**Para la próxima:** abrir el tablero en internet, mirar distintos meses y zonas, y contar qué mes
fue el más alto y por qué.

## 2026-10-05 — Espacio preparado en el PC
**Quería:** (sesión de Jorge) dejar el espacio de Danna listo para trabajar en local.
**Hicimos:** clon aparte del repo en `C:\Danna\URJTA_SO` (fuera de `C:\SERVER`, donde corre la app
de producción), rama `danna` creada y respaldada en GitHub (`origin/danna`). Permisos de Claude Code
en `C:\Danna\URJTA_SO\.claude\settings.local.json` (no se sube a git): escritura bloqueada en
`C:\SERVER` y `C:\BD`, lectura de `.env` bloqueada, y modo de permisos por defecto (Claude pide
permiso antes de editar o ejecutar).
**Aprendí:** —
**Commits:** este mismo commit (`danna: espacio preparado en local`).
**Para la próxima:** abrir Claude Code en `C:\Danna\URJTA_SO\danna` y empezar la primera sesión
de Danna.
**Ideas para Jorge:** la rama `danna` parte del `main` publicado en GitHub, que va atrás del `main`
del servidor. Para leer el código actual, Danna puede mirar `C:\SERVER` (solo lectura).

## 2026-10-05 — Nace el espacio de Danna
**Quería:** (sesión de Jorge) armarle a Danna un espacio propio para aprender IA y el contrato de
cobranza, con registro de todo y posibilidad de volver atrás.
**Hicimos:** carpeta `danna/` con reglas para Claude (`CLAUDE.md`), guía de inicio (`LEEME.md`),
esta bitácora, y el tablero versión 0 (`tablero/index.html`).
**Aprendí:** —
**Commits:** ver `git log --oneline -- danna/`
**Para la próxima:** primera sesión de Danna: revisar el flujo de una orden con Jorge y hacer su
primer cambio al tablero.
