# Sistema URJTA

Aplicación web de terreno para URJTA Ingeniería & Servicios: revisión de cortes, materiales,
combustible, búsqueda geo, y caja chica con flujo de solicitud/aprobación/rendición.

Ver [docs/PLAN_FORMALIZACION.md](docs/PLAN_FORMALIZACION.md) para el plan de trabajo y alcance.

## Requisitos

- Python 3.14+
- `pip install -r requirements.txt`

## Configuración local

1. Copia `.env.example` a `.env` y completa los valores reales (contraseña de admin, PIN de
   usuarios, clave de sesión). **El `.env` real nunca se sube al repositorio.**
2. Crea las carpetas `data/` y `fotos/` en la raíz del proyecto (no se versionan — contienen
   datos reales de clientes y fotos de terreno, solo existen en el servidor de producción).
3. Corre la app: `python app.py` — sirve en `http://localhost:5000`.

### Desarrollo local (fuera del servidor de producción)

Para trabajar en un equipo que no es el PC de producción — sin acceso a `C:\SERVER\` ni a los
datos reales:

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # cualquier valor sirve, es solo para desarrollo
python seed_dev.py          # crea data/ con datos FICTICIOS
python app.py
```

Agrega estas líneas al `.env` para que la app use carpetas locales en vez de las de producción:

```
URJTA_DATA_DIR=./data
URJTA_FOTOS_DIR=./fotos
```

También existe `URJTA_PIPELINE_DIR` para apuntar a las salidas de Urjta-Cobranza
(`seguimiento.parquet`, `eepp_final.csv`). Sin él, Cobranza muestra el aviso de "no se
encontró el pipeline" — es lo esperado fuera del PC de producción.

Usuarios que crea `seed_dev.py` (el PIN es el de tu `.env`):

| Código | Nombre | Cargo | Sirve para probar |
|---|---|---|---|
| 1001 | PEREZ JUAN | OPERADOR | ve solo sus propios cortes |
| 2001 | CASTRO ANDREA | SUPERVISOR | ve todo el terreno |
| 3001 | SOTO PATRICIA | ADMINISTRADOR DE CONTRATO | caja chica: solo lo propio |
| 4001 | VEGA RICARDO | DIRECCION | ve todo, aprueba caja chica |

`seed_dev.py` nunca sobrescribe un CSV que ya exista, así que es seguro correrlo de nuevo.

## Estructura

- `app.py` — aplicación Flask (rutas, lógica de negocio)
- `sync_pipeline.py` — ingesta desde el pipeline de datos real (Urjta-Cobranza)
- `seed_dev.py` — genera datos ficticios para desarrollo local (no toca producción)
- `templates/` — vistas HTML (Jinja2)
- `static/` — logo, íconos, manifest PWA
- `docs/` — documentación del proyecto
- `data/`, `fotos/` — **no versionados**, datos reales solo en el servidor de producción

## Roles de usuario

| Cargo | Acceso |
|---|---|
| OPERADOR | Terreno (Revisión Cortes, Materiales, Combustible, Geo) — solo lo propio |
| ADMINISTRATIVO / SUPERVISOR | Terreno — todo |
| ADMINISTRADOR DE CONTRATO | Terreno — todo, + Caja Chica (solo sus propias solicitudes) |
| DIRECCION / GERENCIA | Todo, + Caja Chica (todas las solicitudes) |

El panel `/admin` usa una contraseña separada (`URJTA_ADMIN_PASS`), independiente del login por
rol — es la vista maestra de todos los módulos.

## Producción

Corre sobre un servidor de desarrollo de Flask en un PC de URJTA, expuesto por un túnel
`cloudflared` (`cloudflared.exe`, no versionado — se descarga aparte). Ver
`docs/PLAN_FORMALIZACION.md` para el plan de migrar a un despliegue más formal.
