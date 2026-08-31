# Plan de Formalización — Sistema URJTA

**Fecha:** 2026-07-15
**Responsable:** Jorge (solo, con Claude Code)
**Estado:** Borrador para revisión — pendiente de aprobación de alcance

---

## 1. Visión

**Ahora (Fase 1, lo que estamos construyendo):** dejar sólida, documentada y corriendo con datos reales
la versión URJTA del sistema — terreno (cortes, materiales, combustible, geo), caja chica con aprobación,
y roles de usuario. Esta es la versión piloto a probar en producción con el contrato real de corte y repo.

**Después (visión futura, fuera de alcance por ahora):** convertir esto en una solución de apoyo a la
toma de decisiones y control de gastos/operatividad para otras empresas del rubro. El modelo concreto
(plantilla que cada empresa instala vs. SaaS multiempresa) todavía no está decidido — depende de escuchar
a esas empresas más adelante. No se toman decisiones de arquitectura ahora en función de esto; solo se
evita cerrar puertas innecesariamente.

## 2. Estado actual (auditoría honesta)

**Lo que funciona hoy:**
- 6 módulos operativos: Revisión de Cortes, Materiales, Combustible, Buscar Geo, Caja Chica, Admin
- Login por PIN con 3 roles (Operador / Administrativo-Supervisor / Administrador de Contrato)
- Fotos con marca de agua, GPS, generación de reportes CSV descargables
- Identidad visual propia (logo, paleta de marca)

**Brechas técnicas que hoy son aceptables pero no serían aceptables en un producto formal:**
- **Sin control de versiones.** No hay git. Cada cambio se aplica directo al archivo en producción.
- **Persistencia en CSV**, no en una base de datos real. Sin transacciones: dos escrituras simultáneas
  pueden corromper un archivo. Ya tuvimos un incidente de este tipo (bloqueo de archivo por Excel abierto).
- **Secretos en el código fuente** (`ADMIN_PASS`, `secret_key`, PIN de usuario) en texto plano en `app.py`.
- **Sin respaldos automáticos.** Los CSV y las fotos solo existen en un disco.
- **Servidor de desarrollo de Flask** expuesto por túnel cloudflared — funciona, pero no es apto para
  carga real sostenida ni para más de un puñado de usuarios concurrentes.
- **Sin pruebas automatizadas.** Cada cambio se valida manualmente (lo hemos hecho bien hasta ahora, pero
  no escala).

Ninguna de estas brechas es urgente para seguir usándolo como hasta ahora. Todas se vuelven relevantes
en el momento en que decimos "esto es un producto formal" o "otras empresas lo van a usar".

## 3. Alcance de la Fase 1 (lo que SÍ se hace ahora)

1. Formalización técnica de la base (git, base de datos real, secretos fuera del código, respaldos).
2. Conexión al pipeline real de datos: ingesta automática desde los archivos `.parquet` que ya genera
   Jorge desde otras apps (carpeta pendiente de revisión — ver sección 5).
3. Dashboards por rol (ver sección 6).
4. Piloto en producción con el contrato real de corte y repo del mes.
5. Documentación técnica y de usuario.

**Lo que NO se hace ahora** (explícitamente fuera de alcance de esta fase): multi-tenencia real,
cuentas/facturación para otras empresas, internacionalización, cualquier trabajo orientado a un cliente
externo distinto de URJTA.

## 4. Módulos — inventario

| Módulo | Estado | Notas |
|---|---|---|
| Revisión de Cortes | ✅ Estable | Filtro por rol, marca de pago, geo |
| Materiales | ✅ Estable | Identidad bloqueada por rol |
| Combustible | ✅ Estable | Identidad bloqueada por rol |
| Buscar Geo | ✅ Estable | Índice cacheado, 190k+ filas |
| Caja Chica | ✅ Estable | Solicitud → aprobación → rendición con IVA |
| Admin | ✅ Estable | Panel maestro, separado del login por rol |
| Asistencia (QR) | 🆕 Listo para piloto | QR de jornada rotativo, credenciales, nómina diaria y mensual — ver `ASISTENCIA_QR.md` |
| Base de datos real | ⏳ Pendiente | Migrar de CSV a SQLite |
| Control de versiones | ⏳ Pendiente | Git init + disciplina de commits |
| Ingesta de pipeline (parquet) | ⏳ Pendiente | Depende de revisar la carpeta de Jorge |
| Dashboards por rol | ⏳ Pendiente | Ver sección 6 |
| Documentación | ⏳ Pendiente | README, diccionario de datos, manual de usuario |

## 5. Pipeline de datos real — CONFIRMADO (2026-07-15)

`C:\BD\Drive\TI\Urjta-Cobranza` **no es solo una carpeta con un parquet** — es un proyecto de BI/ETL
propio, ya formalizado (pipeline canónico `seguimiento_nyr.py` que replica un `.qvs` de Qlik Sense,
medidas de negocio en `medidas.py`, dashboard en construcción, validación de regresión, inventario de
decisiones vivo en `docs/INVENTARIO.md`). Es un proyecto hermano, no un simple insumo.

**Salida real:** `C:\BD\SGC\Salidas\seguimiento.parquet` — 229.641 filas × 116 columnas, actualizado en
vivo (corre con datos de producción).

**Filtro confirmado para "cortes pendientes"** (lo que necesita `/campo`):
`TIPO_RESULTADO == 'PENDIENTE' AND TIPO_ACCION == 'CORTE'`, sobre `PERIODO_ORDEN` = período actual.
Validado: 722 pendientes en 202607 (julio 2026).

**Mapeo de columnas a `clientes.csv`** (casi 1:1):

| clientes.csv | seguimiento.parquet |
|---|---|
| ID_SERVICIO | ID_SERVICIO |
| DEUDA | DEUDA |
| ANTIGUEDAD | ANTIGUEDAD |
| TIPO CORTE | TIPO_CORTE |
| DIRECCION | DIRECCION |
| MEDIDOR | MEDIDOR |
| LOCALIDAD | LOCALIDAD_C |
| PAGO | PAGO_FLAG |
| OPERADOR | **RESPONSABLE** (no `OPERADOR` — ver nota) |

**Nota sobre asignación de operador:** el corte pendiente trae un campo `RESPONSABLE` (asignado en
NyR/Qlik antes de llegar a terreno) — distinto de `OPERADOR`, que solo se llena cuando el PDA ya
ejecutó la visita. Cobertura real: 507/722 (70%) de los pendientes de julio 2026 ya tienen
`RESPONSABLE`. El 30% restante llega sin asignar — a definir si se muestra "sin asignar" o si se
resuelve por otra vía.

**Próximo paso concreto:** script de ingesta que lea `seguimiento.parquet`, filtre pendientes del
período vigente, mapee columnas (incluido `RESPONSABLE → OPERADOR`), y genere una vista previa para
validar contra la carga manual actual antes de reemplazarla en el panel de Admin.

## 6. Roles y vistas (dashboards) — DECIDIDO: liviano y operativo, sin duplicar

Confirmado con Jorge: los dashboards de esta app se limitan a la **actividad operativa que ocurre
dentro de esta app** (registros de campo, materiales, combustible, caja chica). Las métricas
contractuales (SLA, Efectividad, EEPP, Improcedencias) **no se replican aquí** — ya existen en el
dashboard de Urjta-Cobranza. Evita mantener dos sistemas mostrando lo mismo.

| Rol | Qué necesita ver | Fuente |
|---|---|---|
| Operador | Sus cortes pendientes/pagados, su propio avance | Datos propios de esta app |
| Administrativo / Supervisor | Avance operativo por operador/localidad (registros en esta app) | Datos propios de esta app |
| Administrador de Contrato | Gasto de caja chica por categoría y mes, saldo, solicitudes propias | Único de esta app |
| Dirección/Gerencia | **Enlace directo** al dashboard de Urjta-Cobranza (KPIs contractuales) | No se construye nada nuevo |

*Las métricas exactas de cada dashboard se definen junto con Jorge antes de construir — esto es un
punto de partida, no un diseño cerrado.*

## 7. Hoja de ruta y estimación de horas

| Fase | Contenido | Horas estimadas |
|---|---|---|
| 0 — Formalización técnica | Git, secretos fuera del código, migración a SQLite, respaldos, pruebas básicas | 19–28 h |
| 1 — Pipeline de datos | Script de ingesta desde `seguimiento.parquet`, mapeo confirmado, botón de sincronización | 8–14 h |
| 2 — Dashboards | Definir métricas + construir 3 vistas operativas propias (Dirección se enlaza a Urjta-Cobranza) | 13–17 h |
| 3 — Piloto en producción | Acompañamiento durante el ciclo mensual real, corrección de bugs | 8–12 h |
| 4 — Documentación | README técnico, diccionario de datos, manual de usuario | 8–10 h |
| **Total** | | **56–81 h** |

**Para la pregunta de tu jefe:** a un ritmo de ~2 horas diarias (10 h/semana), esto toma entre
**5.6 y 8.1 semanas** (1.3–2 meses) para completar las 5 fases. Solo la Fase 0 (la formalización
técnica base) toma entre 3 y 4 semanas a ese ritmo.

*Nota: son estimaciones de planificación, no un compromiso cerrado — el desarrollo asistido por IA
reduce tiempos pero la validación con datos reales (Fase 3) puede traer ajustes no previstos.*

## 8. Decisiones pendientes

- [x] ~~Revisar la carpeta con las apps que generan el parquet~~ — hecho 2026-07-15, ver sección 5
- [x] ~~Dashboards: liviano vs. absorber métricas de Urjta-Cobranza~~ — decidido: liviano, sin duplicar
- [ ] Definir métricas exactas de los 3 dashboards operativos propios
- [ ] Qué hacer con el 30% de cortes pendientes sin `RESPONSABLE` asignado (¿"sin asignar" visible, o se resuelve antes de llegar a esta app?)
- [ ] Confirmar si existe un rol "Dirección/Gerencia" real o si Administrador de Contrato ya cumple ese rol
- [ ] Modelo de exportación a otras empresas (plantilla vs. SaaS) — decisión futura, no bloquea esta fase
