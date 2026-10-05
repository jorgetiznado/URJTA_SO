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
