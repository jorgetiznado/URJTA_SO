# Sistema URJTA

Aplicación web de terreno para URJTA Ingeniería & Servicios: revisión de cortes, materiales,
combustible, búsqueda geo, caja chica con flujo de solicitud/aprobación/rendición, y nómina de
asistencia por QR.

Ver [docs/PLAN_FORMALIZACION.md](docs/PLAN_FORMALIZACION.md) para el plan de trabajo y alcance.

## Requisitos

- Python 3.14+
- `pip install -r requirements.txt` (flask, pandas, pillow, pyarrow, segno)

## Configuración local

1. Copia `.env.example` a `.env` y completa los valores reales (contraseña de admin, PIN de
   usuarios, clave de sesión). **El `.env` real nunca se sube al repositorio.**
2. Crea las carpetas `data/` y `fotos/` en la raíz del proyecto (no se versionan — contienen
   datos reales de clientes y fotos de terreno, solo existen en el servidor de producción).
3. Corre la app: `python app.py` — sirve en `http://localhost:5000`.

## Estructura

- `app.py` — aplicación Flask (rutas, lógica de negocio)
- `sync_pipeline.py` — ingesta desde el pipeline de datos real (Urjta-Cobranza)
- `asistencia.py` — lógica de la nómina por QR (tokens firmados, cálculo de jornada)
- `test_asistencia.py` — pruebas de esa lógica (`python test_asistencia.py`)
- `templates/` — vistas HTML (Jinja2)
- `Static/` — logo, íconos, manifest PWA
- `docs/` — documentación del proyecto
- `data/`, `fotos/` — **no versionados**, datos reales solo en el servidor de producción

## Roles de usuario

| Cargo | Acceso |
|---|---|
| OPERADOR | Terreno (Revisión Cortes, Materiales, Combustible, Geo) — solo lo propio, + marcar su asistencia |
| ADMINISTRATIVO / SUPERVISOR | Terreno — todo, + QR de jornada y nómina de asistencia |
| ADMINISTRADOR DE CONTRATO | Terreno — todo, + Caja Chica (solo sus propias solicitudes), + asistencia |
| DIRECCION / GERENCIA | Todo, + Caja Chica (todas las solicitudes) |

## Módulos

| Módulo | Ruta | Documentación |
|---|---|---|
| Revisión de Cortes | `/campo` | — |
| Materiales | `/materiales` | — |
| Combustible | `/combustible` | — |
| Buscar Geo | `/geo` | — |
| Caja Chica | `/caja-chica` | [ADMIN_COBRANZA_DISENO.md](docs/ADMIN_COBRANZA_DISENO.md) |
| Asistencia (QR) | `/asistencia` | [ASISTENCIA_QR.md](docs/ASISTENCIA_QR.md) |
| Administración | `/admin` | — |

El panel `/admin` usa una contraseña separada (`URJTA_ADMIN_PASS`), independiente del login por
rol — es la vista maestra de todos los módulos.

## Producción

Corre sobre un servidor de desarrollo de Flask en un PC de URJTA, expuesto por un túnel
`cloudflared` (`cloudflared.exe`, no versionado — se descarga aparte). Ver
`docs/PLAN_FORMALIZACION.md` para el plan de migrar a un despliegue más formal.
