from flask import Flask, render_template, request, redirect, url_for, send_file, session
import pandas as pd
import os
from datetime import datetime
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import sync_pipeline


def _cargar_env(ruta='.env'):
    """Carga variables desde un archivo .env local (no versionado en git) al entorno.
    No sobrescribe variables que ya estén definidas en el sistema."""
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, _, valor = linea.partition('=')
            os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()

app = Flask(__name__)
app.secret_key = os.environ['URJTA_SECRET_KEY']

DATA_FOLDER          = r'C:\SERVER\data'
FOTOS_FOLDER         = r'C:\SERVER\fotos'
CSV_PATH             = os.path.join(DATA_FOLDER, 'clientes.csv')
RESULTADOS_PATH      = os.path.join(DATA_FOLDER, 'resultados.csv')
MATERIALES_PATH      = os.path.join(DATA_FOLDER, 'materiales.csv')
OPERADORES_PATH      = os.path.join(DATA_FOLDER, 'operadores.csv')
MAT_USADOS_PATH      = os.path.join(DATA_FOLDER, 'materiales_usados.csv')
COMBUSTIBLE_PATH     = os.path.join(DATA_FOLDER, 'combustible.csv')
GEO_CATASTRO_PATH    = os.path.join(DATA_FOLDER, 'Geo_Catastro.csv')
CAJA_CHICA_PATH      = os.path.join(DATA_FOLDER, 'caja_chica.csv')

ADMIN_PASS  = os.environ['URJTA_ADMIN_PASS']
USUARIO_PIN = os.environ['URJTA_USUARIO_PIN']

CARGO_OPERADOR       = 'OPERADOR'
CARGOS_SUPERVISION   = {'ADMINISTRATIVO', 'SUPERVISOR'}
CARGO_ADMIN_CONTRATO = 'ADMINISTRADOR DE CONTRATO'
CARGOS_DIRECCION     = {'DIRECCION', 'GERENCIA'}  # el más alto, por sobre Admin. de Contrato

os.makedirs(DATA_FOLDER,  exist_ok=True)
os.makedirs(FOTOS_FOLDER, exist_ok=True)


def fotos_folder(modulo):
    """Carpeta de fotos de un módulo (ej. 'cortes', 'materiales'). La crea si no existe.
    Para agregar un módulo nuevo, solo define aquí una constante FOTOS_<MODULO> = fotos_folder('<modulo>')."""
    path = os.path.join(FOTOS_FOLDER, modulo)
    os.makedirs(path, exist_ok=True)
    return path


FOTOS_CORTES_FOLDER      = fotos_folder('cortes')
FOTOS_MATERIALES_FOLDER  = fotos_folder('materiales')
FOTOS_COMBUSTIBLE_FOLDER = fotos_folder('combustible')
FOTOS_CAJA_CHICA_FOLDER  = fotos_folder('caja_chica')

TIPOS_CORTE_OPCIONES = [
    'CANERIA VEREDA CON PAVIMENTO',
    'CANERIA VEREDA SIN PAVIMENTO',
    'LLAVE DE PASO',
    'LLAVE DE VEREDA',
    'MATRIZ CON PAVIMENTO',
    'MATRIZ SIN PAVIMENTO',
    'RETIRO LLAVE DE PASO',
]

IMPROCEDENCIAS = [
    'ARRANQUE COLECTIVO',
    'ARRANQUE NO UBICADO',
    'CANCELADO',
    'CASA CERRADA CORTABLE',
    'CASA CERRADA NO CORTABLE',
    'CASA DESHABITADA',
    'CLIENTE SE NIEGA AL CORTE',
    'CORTE ANTERIOR',
    'DIRECCION NO UBICADA',
    'ERROR DE CATASTRO',
    'INSTALACION DEFECTUOSA',
    'SITIO ERIAZO',
]

TIPOS_ACCION = ['CORTE', 'REPO', 'CAMBIO MAP', 'REGULARIZACIÓN']

CAJA_CHICA_CATEGORIAS = [
    'COMBUSTIBLE',
    'MATERIALES E INSUMOS',
    'MANTENCIÓN VEHÍCULOS',
    'PEAJES Y ESTACIONAMIENTO',
    'INSUMOS DE OFICINA',
    'ALIMENTACIÓN / COLACIÓN',
    'OTROS',
]

CAJA_CHICA_TIPOS_DOC = ['BOLETA', 'FACTURA', 'SIN DOCUMENTO']

CAJA_CHICA_COLUMNS = [
    'ID', 'FECHA_SOLICITUD', 'SOLICITANTE', 'CATEGORIA', 'DESCRIPCION', 'MONTO_SOLICITADO',
    'ESTADO', 'FECHA_APROBACION', 'COMENTARIO_APROBACION',
    'TIPO_DOCUMENTO', 'NUM_DOCUMENTO', 'RUT_PROVEEDOR', 'RAZON_SOCIAL',
    'MONTO_NETO', 'IVA', 'MONTO_TOTAL', 'FOTO_DOCUMENTO', 'FECHA_RENDICION',
    'LATITUD', 'LONGITUD',
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def read_csv_safe(path):
    if not os.path.exists(path):
        return None
    for enc in ['utf-8-sig', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc, sep=None, engine='python')
            df.columns = df.columns.str.strip()
            return df
        except UnicodeDecodeError:
            continue
    return None


def get_df():
    df = read_csv_safe(CSV_PATH)
    if df is None:
        return None
    if 'FECHA_CORTE' in df.columns:
        df['PERIODO'] = pd.to_datetime(
            df['FECHA_CORTE'], dayfirst=True, errors='coerce'
        ).dt.strftime('%Y%m')
    if 'ANTIGUEDAD' in df.columns:
        antiguedad_num = pd.to_numeric(df['ANTIGUEDAD'], errors='coerce')
        df['TIPO_DEUDA'] = antiguedad_num.apply(
            lambda x: 'INCOBRABLE' if pd.notna(x) and x >= 6 else 'NORMAL'
        )
    if 'LOCALIDAD' not in df.columns:
        df['LOCALIDAD'] = ''
    if 'PAGO' in df.columns:
        df['PAGADO'] = df['PAGO'].astype(str).str.strip() == '1'
    else:
        df['PAGADO'] = False
    return df


def get_resultados():
    if not os.path.exists(RESULTADOS_PATH):
        return pd.DataFrame()
    df = pd.read_csv(RESULTADOS_PATH, dtype=str, sep=None, engine='python')
    df.columns = df.columns.str.strip()
    return df


def get_materiales():
    df = read_csv_safe(MATERIALES_PATH)
    if df is None:
        return []
    return df.to_dict('records')


def get_operadores():
    df = read_csv_safe(OPERADORES_PATH)
    if df is None:
        return []
    return df.to_dict('records')


def get_operadores_login():
    """Operadores habilitados para iniciar sesión: activos y no ficticios."""
    df = read_csv_safe(OPERADORES_PATH)
    if df is None:
        return []
    if 'ESTADO' in df.columns:
        df = df[df['ESTADO'].fillna('').str.strip().str.upper() == 'ACTIVO']
    if 'CARGO' in df.columns:
        df = df[df['CARGO'].fillna('').str.strip().str.upper() != 'FICTICIO']
    return df.sort_values('NOMBRE').to_dict('records')


def _nombre_normalizado(nombre):
    """Normaliza un nombre a un conjunto de palabras en mayúsculas, para comparar
    'Jorge Silva' con 'SILVA JORGE' (o con duplicados) sin importar orden/caso."""
    return frozenset(str(nombre or '').upper().split())


def usuario_actual():
    if not session.get('user_codigo'):
        return None
    return {
        'codigo': session.get('user_codigo'),
        'nombre': session.get('user_nombre'),
        'cargo':  session.get('user_cargo'),
        'valor':  session.get('user_valor'),  # "CODIGO - NOMBRE", mismo formato de los selects existentes
    }


def puede_ver_todo(usuario):
    return bool(usuario) and usuario['cargo'] in CARGOS_SUPERVISION | {CARGO_ADMIN_CONTRATO} | CARGOS_DIRECCION


def es_direccion(usuario):
    return bool(usuario) and usuario['cargo'] in CARGOS_DIRECCION


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('user_codigo'):
            return redirect(url_for('login', next=request.path))
        return vista(*args, **kwargs)
    return envoltura


def acceso_caja_chica(vista):
    """Admin. de Contrato (solo lo propio) y Dirección/Gerencia (ve todo, por sobre Admin. de Contrato)."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('user_codigo'):
            return redirect(url_for('login', next=request.path))
        cargo = session.get('user_cargo')
        if cargo != CARGO_ADMIN_CONTRATO and cargo not in CARGOS_DIRECCION:
            return render_template('sin_permiso.html'), 403
        return vista(*args, **kwargs)
    return envoltura


def guardar_csv_subido(archivo, destino):
    """Guarda el CSV subido. Devuelve un mensaje de error legible si falla, o None si todo bien."""
    try:
        archivo.save(destino)
        return None
    except PermissionError:
        return (f"No se pudo guardar {os.path.basename(destino)}: el archivo está abierto "
                f"en otro programa (ej. Excel). Ciérralo e inténtalo de nuevo.")
    except OSError as e:
        return f"No se pudo guardar {os.path.basename(destino)}: {e}"


def get_caja_chica():
    """DataFrame completo de solicitudes de caja chica (todas las columnas como texto)."""
    if not os.path.exists(CAJA_CHICA_PATH):
        return pd.DataFrame(columns=CAJA_CHICA_COLUMNS)
    df = pd.read_csv(CAJA_CHICA_PATH, dtype=str, sep=';').fillna('')
    df.columns = df.columns.str.strip()
    for col in CAJA_CHICA_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    return df[CAJA_CHICA_COLUMNS]


def guardar_caja_chica(df):
    df.to_csv(CAJA_CHICA_PATH, sep=';', index=False)


def _next_caja_chica_id(df):
    if df.empty:
        return '1'
    return str(df['ID'].astype(int).max() + 1)


_geo_cache = {'mtime': None, 'index': {}}


def _parse_num(valor):
    try:
        return float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        return None


def get_geo_index():
    """Índice SERVICIO -> coordenadas, cacheado en memoria (se recarga si el CSV cambia)."""
    if not os.path.exists(GEO_CATASTRO_PATH):
        return {}
    mtime = os.path.getmtime(GEO_CATASTRO_PATH)
    if _geo_cache['mtime'] == mtime:
        return _geo_cache['index']

    df = read_csv_safe(GEO_CATASTRO_PATH)
    index = {}
    if df is not None and 'SERVICIO' in df.columns:
        for row in df.to_dict('records'):
            sid = str(row.get('SERVICIO', '')).strip()
            if not sid:
                continue
            index[sid] = {
                'servicio':  sid,
                'utm_norte': _parse_num(row.get('UTM NORTE (Y)')),
                'utm_este':  _parse_num(row.get('UTM ESTE (X)')),
                'lat':       _parse_num(row.get('LATITUDE')),
                'lon':       _parse_num(row.get('LONGITUDE')),
                'cliente':   row.get('CLIENTE', ''),
                'direccion': row.get('DIRECCION', ''),
                'medidor':   row.get('MEDIDOR', ''),
                'diametro':  row.get('DIAMETRO', ''),
                'localidad': row.get('LOCALIDAD', ''),
                'marca':     row.get('MARCA', ''),
            }
    _geo_cache['mtime'] = mtime
    _geo_cache['index'] = index
    return index


def procesar_fotos_async(bytes_list, referencia, carpeta):
    import threading, io as _io
    def _procesar():
        for img_bytes, fname in bytes_list:
            try:
                img = Image.open(_io.BytesIO(img_bytes)).convert('RGB')
                img.thumbnail((1280, 1280), Image.LANCZOS)
                draw = ImageDraw.Draw(img)
                w, h = img.size
                ts_texto = datetime.now().strftime('%d/%m/%Y  %H:%M:%S')
                texto = f"URJTA  |  {ts_texto}  |  {referencia}"
                font_size = max(24, h // 28)
                try:
                    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", font_size)
                except Exception:
                    try:
                        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
                    except Exception:
                        font = ImageFont.load_default()
                padding = 12
                bar_h = font_size + padding * 2
                draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0))
                draw.text((padding, h - bar_h + padding), texto, fill='white', font=font)
                img.save(os.path.join(carpeta, fname), 'JPEG', quality=70, optimize=True)
            except Exception as e:
                print(f"Error foto {fname}: {e}")
    threading.Thread(target=_procesar, daemon=True).start()


# ─── Landing ──────────────────────────────────────────────────────────────────

@app.route('/')
def landing():
    return render_template('landing.html', usuario=usuario_actual())


# ─── Login de usuario (terreno / caja chica) ─────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.values.get('next') or url_for('landing')

    if request.method == 'POST':
        codigo = request.form.get('operador_codigo', '')
        pin    = request.form.get('pin', '')
        df = read_csv_safe(OPERADORES_PATH)
        fila = df[df['CODIGO'] == codigo] if df is not None else None

        if pin == USUARIO_PIN and fila is not None and not fila.empty:
            row = fila.iloc[0]
            session['user_codigo'] = codigo
            session['user_nombre'] = row['NOMBRE']
            session['user_cargo']  = str(row.get('CARGO', '')).strip().upper()
            session['user_valor']  = f"{codigo} - {row['NOMBRE']}"
            return redirect(next_url)

        return render_template('login.html', operadores=get_operadores_login(),
                               next=next_url, error=True)

    return render_template('login.html', operadores=get_operadores_login(),
                           next=next_url, error=False)


@app.route('/logout')
def logout():
    session.pop('user_codigo', None)
    session.pop('user_nombre', None)
    session.pop('user_cargo', None)
    session.pop('user_valor', None)
    return redirect(url_for('landing'))


# ─── Admin ────────────────────────────────────────────────────────────────────

def _admin_requerido():
    return not session.get('admin')


@app.route('/admin')
def admin():
    if _admin_requerido():
        return render_template('login_admin.html', error=False)

    df   = get_df()
    df_r = get_resultados()
    df_cc = get_caja_chica()

    stats = {
        'total_clientes':    len(df) if df is not None else 0,
        'total_gestionados': len(df_r),
        'csv_cargado':       os.path.exists(CSV_PATH),
        'mat_cargado':       os.path.exists(MATERIALES_PATH),
        'op_cargado':        os.path.exists(OPERADORES_PATH),
        'cc_pendientes':     len(df_cc[df_cc['ESTADO'] == 'PENDIENTE']),
    }

    return render_template('admin_hub.html', stats=stats, error=request.args.get('error'))


@app.route('/admin/clientes')
def admin_clientes():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df   = get_df()
    df_r = get_resultados()

    stats = {
        'total_clientes':    len(df) if df is not None else 0,
        'total_gestionados': len(df_r),
        'csv_cargado':       os.path.exists(CSV_PATH),
    }

    resumen = []
    if not df_r.empty and 'RESULTADO' in df_r.columns:
        resumen = df_r.groupby('RESULTADO').size().reset_index(name='CANTIDAD').to_dict('records')

    ultimos = df_r.tail(20).iloc[::-1].to_dict('records') if not df_r.empty else []

    return render_template('admin_clientes.html', stats=stats, resumen=resumen,
                           ultimos=ultimos, error=request.args.get('error'))


@app.route('/admin/materiales')
def admin_materiales_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df_m = read_csv_safe(MAT_USADOS_PATH) if os.path.exists(MAT_USADOS_PATH) else pd.DataFrame()

    stats = {
        'total_mat_usados': len(df_m) if df_m is not None else 0,
        'mat_cargado':      os.path.exists(MATERIALES_PATH),
    }
    ultimos_mat = df_m.tail(10).iloc[::-1].to_dict('records') if df_m is not None and not df_m.empty else []

    return render_template('admin_materiales.html', stats=stats, ultimos_mat=ultimos_mat,
                           error=request.args.get('error'))


@app.route('/admin/combustible')
def admin_combustible_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df_comb = read_csv_safe(COMBUSTIBLE_PATH) if os.path.exists(COMBUSTIBLE_PATH) else pd.DataFrame()
    stats = {'total_combustible': len(df_comb) if df_comb is not None else 0}
    ultimos_comb = df_comb.tail(10).iloc[::-1].to_dict('records') if df_comb is not None and not df_comb.empty else []

    return render_template('admin_combustible.html', stats=stats, ultimos_comb=ultimos_comb)


@app.route('/admin/operadores')
def admin_operadores_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    operadores = get_operadores()
    stats = {'op_cargado': os.path.exists(OPERADORES_PATH), 'total_operadores': len(operadores)}
    return render_template('admin_operadores.html', stats=stats, operadores=operadores)


@app.route('/admin/caja-chica')
def admin_caja_chica_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df_cc = get_caja_chica()
    stats = {
        'cc_pendientes':    len(df_cc[df_cc['ESTADO'] == 'PENDIENTE']),
        'cc_aprobadas':     len(df_cc[df_cc['ESTADO'] == 'APROBADA']),
        'cc_rendidas':      len(df_cc[df_cc['ESTADO'] == 'RENDIDA']),
        'cc_total_rendido': pd.to_numeric(
            df_cc[df_cc['ESTADO'] == 'RENDIDA']['MONTO_TOTAL'], errors='coerce'
        ).fillna(0).sum(),
    }
    cc_pendientes = df_cc[df_cc['ESTADO'] == 'PENDIENTE'].to_dict('records')
    cc_aprobadas  = df_cc[df_cc['ESTADO'] == 'APROBADA'].to_dict('records')
    cc_rendidas   = df_cc[df_cc['ESTADO'] == 'RENDIDA'].tail(15).iloc[::-1].to_dict('records')

    return render_template('admin_caja_chica.html', stats=stats,
                           cc_pendientes=cc_pendientes, cc_aprobadas=cc_aprobadas,
                           cc_rendidas=cc_rendidas)


@app.route('/admin/cobranza')
def admin_cobranza_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df = get_df()
    stats = {'total_clientes': 0, 'total_pagado': 0, 'total_sin_pago': 0,
             'monto_pagado': 0, 'monto_sin_pago': 0}
    if df is not None and not df.empty:
        pagados = df[df['PAGADO']]
        sin_pago = df[~df['PAGADO']]
        stats['total_clientes']  = len(df)
        stats['total_pagado']    = len(pagados)
        stats['total_sin_pago']  = len(sin_pago)
        stats['monto_pagado']    = pd.to_numeric(pagados['DEUDA'], errors='coerce').fillna(0).sum()
        stats['monto_sin_pago']  = pd.to_numeric(sin_pago['DEUDA'], errors='coerce').fillna(0).sum()

    pipeline_disponible = os.path.exists(sync_pipeline.PARQUET_PATH)

    return render_template('admin_cobranza.html', stats=stats,
                           pipeline_disponible=pipeline_disponible)


@app.route('/admin/login', methods=['POST'])
def admin_login():
    if request.form.get('clave') == ADMIN_PASS:
        session['admin'] = True
        return redirect(url_for('admin'))
    return render_template('login_admin.html', error=True)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('landing'))


@app.route('/admin/sincronizar-pipeline')
def sincronizar_pipeline_preview():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    error = None
    df = pd.DataFrame(columns=sync_pipeline.COLUMNAS_CLIENTES)
    periodo = None
    try:
        periodo = sync_pipeline.periodo_mas_reciente()
        df = sync_pipeline.obtener_pendientes(periodo='actual')
    except FileNotFoundError:
        error = f"No se encontró el archivo del pipeline en {sync_pipeline.PARQUET_PATH}."
    except Exception as e:
        error = f"Error leyendo el pipeline: {e}"

    return render_template('sync_preview.html',
                           total=len(df),
                           periodo=periodo,
                           sin_operador=int(df['OPERADOR'].isna().sum()) if not df.empty else 0,
                           muestra=df.head(15).to_dict('records'),
                           error=error)


@app.route('/admin/sincronizar-pipeline/confirmar', methods=['POST'])
def sincronizar_pipeline_confirmar():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    df = sync_pipeline.obtener_pendientes(periodo='actual')

    if os.path.exists(CSV_PATH):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(DATA_FOLDER, f'clientes_backup_{ts}.csv')
        import shutil
        shutil.copy2(CSV_PATH, backup_path)

    df.to_csv(CSV_PATH, sep=';', index=False)
    return redirect(url_for('admin'))


@app.route('/subir-csv', methods=['POST'])
def subir_csv():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    archivo = request.files.get('csv')
    error = None
    if archivo and archivo.filename.endswith('.csv'):
        error = guardar_csv_subido(archivo, CSV_PATH)
    if error:
        return redirect(url_for('admin', error=error))
    return redirect(url_for('admin'))


@app.route('/subir-materiales', methods=['POST'])
def subir_materiales():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    archivo = request.files.get('csv')
    error = None
    if archivo and archivo.filename.endswith('.csv'):
        error = guardar_csv_subido(archivo, MATERIALES_PATH)
    if error:
        return redirect(url_for('admin', error=error))
    return redirect(url_for('admin'))


@app.route('/subir-operadores', methods=['POST'])
def subir_operadores():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    archivo = request.files.get('csv')
    error = None
    if archivo and archivo.filename.endswith('.csv'):
        error = guardar_csv_subido(archivo, OPERADORES_PATH)
    if error:
        return redirect(url_for('admin', error=error))
    return redirect(url_for('admin'))


# ─── Campo ────────────────────────────────────────────────────────────────────

@app.route('/campo')
@login_requerido
def campo():
    usuario = usuario_actual()
    df = get_df()
    df_r = get_resultados()
    clientes, operadores, tipos_corte, periodos, localidades = [], [], [], [], []
    filtros = {}

    if df is not None:
        if not puede_ver_todo(usuario) and 'OPERADOR' in df.columns:
            mi_nombre = _nombre_normalizado(usuario['nombre'])
            df = df[df['OPERADOR'].apply(lambda x: _nombre_normalizado(x) == mi_nombre)]

        if 'OPERADOR'   in df.columns: operadores  = sorted(df['OPERADOR'].dropna().unique())
        if 'TIPO CORTE' in df.columns: tipos_corte = sorted(df['TIPO CORTE'].dropna().unique())
        if 'PERIODO'    in df.columns: periodos    = sorted(df['PERIODO'].dropna().unique(), reverse=True)
        localidades = sorted(df['LOCALIDAD'].dropna().replace('', pd.NA).dropna().unique()) if 'LOCALIDAD' in df.columns else []

        f_op    = request.args.get('operador',   '')
        f_tipo  = request.args.get('tipo_corte', '')
        f_per   = request.args.get('periodo',    '')
        f_deuda = request.args.get('tipo_deuda', '')
        f_loc   = request.args.get('localidad',  '')
        f_pago  = request.args.get('pago',       '')
        filtros = {'operador': f_op, 'tipo_corte': f_tipo, 'periodo': f_per, 'tipo_deuda': f_deuda,
                   'localidad': f_loc, 'pago': f_pago}

        if f_op:    df = df[df['OPERADOR']   == f_op]
        if f_tipo:  df = df[df['TIPO CORTE'] == f_tipo]
        if f_per:   df = df[df['PERIODO']    == f_per]
        if f_deuda: df = df[df['TIPO_DEUDA'] == f_deuda]
        if f_loc:   df = df[df['LOCALIDAD']  == f_loc]
        if f_pago == 'PAGADO':  df = df[df['PAGADO']]
        if f_pago == 'SIN_PAGO': df = df[~df['PAGADO']]

        ids_gestionados = set(df_r['ID_SERVICIO'].str.strip().tolist()) if not df_r.empty else set()
        df['GESTIONADO'] = df['ID_SERVICIO'].str.strip().isin(ids_gestionados)
        df = df.sort_values(['PAGADO', 'GESTIONADO'])
        clientes = df.to_dict('records')

        geo_index = get_geo_index()
        for c in clientes:
            geo = geo_index.get(str(c.get('ID_SERVICIO', '')).strip())
            c['GEO_LAT'] = geo['lat'] if geo else None
            c['GEO_LON'] = geo['lon'] if geo else None

    return render_template('campo.html',
                           clientes=clientes, filtros=filtros,
                           operadores=operadores, tipos_corte=tipos_corte,
                           periodos=periodos, localidades=localidades,
                           usuario=usuario)


# ─── Detalle cliente ──────────────────────────────────────────────────────────

@app.route('/cliente/<id_servicio>')
@login_requerido
def cliente(id_servicio):
    usuario = usuario_actual()
    df = get_df()
    origen = request.args.get('origen', 'campo')
    if df is not None:
        row = df[df['ID_SERVICIO'] == id_servicio]
        if not row.empty:
            c = row.iloc[0].to_dict()
            if not puede_ver_todo(usuario) and _nombre_normalizado(c.get('OPERADOR')) != _nombre_normalizado(usuario['nombre']):
                return redirect(url_for('campo'))
            return render_template('detalle.html', cliente=c,
                                   tipos_corte=TIPOS_CORTE_OPCIONES,
                                   improcedencias=IMPROCEDENCIAS,
                                   operadores=get_operadores(),
                                   origen=origen, usuario=usuario)
    return redirect(url_for('campo'))


# ─── Registrar corte ──────────────────────────────────────────────────────────

@app.route('/registrar', methods=['POST'])
@login_requerido
def registrar():
    usuario = usuario_actual()
    id_servicio      = request.form.get('id_servicio', '')
    operador_registro = request.form.get('operador_registro', '')
    if not puede_ver_todo(usuario):
        operador_registro = usuario['valor']
    resultado        = request.form.get('resultado', '')
    accion           = request.form.get('accion', '')
    tipo_corte_sel   = request.form.get('tipo_corte_sel', '')
    improcedencia    = request.form.get('improcedencia_sel', '')
    observacion      = request.form.get('observacion', '')
    origen           = request.form.get('origen', 'campo')
    fecha_reg        = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    fotos = request.files.getlist('foto')
    fotos_validas = [f for f in fotos if f and f.filename][:4]
    cant_fotos = len(fotos_validas)
    bytes_list, nombres = [], []
    for i, foto in enumerate(fotos_validas, 1):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f"{id_servicio}_{ts}_f{i}.jpg"
        nombres.append(fname)
        bytes_list.append((foto.read(), fname))

    data = {
        'ID_SERVICIO':       id_servicio,
        'OPERADOR_REGISTRO': operador_registro,
        'RESULTADO':         resultado,
        'ACCION':            accion,
        'TIPO_CORTE_SEL':    tipo_corte_sel,
        'IMPROCEDENCIA':     improcedencia,
        'CANT_FOTOS':        cant_fotos,
        'FOTOS':             '|'.join(nombres),
        'FOTO_ORIGEN':       request.form.get('foto_origen', ''),
        'OBSERVACION':       observacion,
        'LATITUD':           request.form.get('latitud', ''),
        'LONGITUD':          request.form.get('longitud', ''),
        'FECHA_REGISTRO':    fecha_reg,
    }
    df_r = pd.DataFrame([data])
    if os.path.exists(RESULTADOS_PATH):
        df_r.to_csv(RESULTADOS_PATH, mode='a', header=False, index=False, sep=';')
    else:
        df_r.to_csv(RESULTADOS_PATH, index=False, sep=';')

    if bytes_list:
        procesar_fotos_async(bytes_list, id_servicio, FOTOS_CORTES_FOLDER)

    return render_template('confirmacion.html',
                           id_servicio=id_servicio,
                           resultado=resultado,
                           origen=origen)


# ─── Materiales ───────────────────────────────────────────────────────────────

@app.route('/materiales')
@login_requerido
def materiales():
    usuario = usuario_actual()
    return render_template('materiales.html',
                           materiales=get_materiales(),
                           operadores=get_operadores(),
                           tipos_accion=TIPOS_ACCION,
                           usuario=usuario)


@app.route('/materiales/registrar', methods=['POST'])
@login_requerido
def registrar_materiales():
    usuario = usuario_actual()
    id_servicio  = request.form.get('id_servicio', '')
    tipo_accion  = request.form.get('tipo_accion', '')
    operador     = request.form.get('operador', '')
    if not puede_ver_todo(usuario):
        operador = usuario['valor']
    observacion  = request.form.get('observacion', '')
    fecha_reg    = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    codigos    = request.form.getlist('mat_codigo')
    nombres_m  = request.form.getlist('mat_nombre')
    cantidades = request.form.getlist('mat_cantidad')
    materiales_str = '|'.join(
        f"{c}:{n}:{q}"
        for c, n, q in zip(codigos, nombres_m, cantidades)
        if c and q
    )

    fotos = request.files.getlist('foto')
    fotos_validas = [f for f in fotos if f and f.filename][:4]
    cant_fotos = len(fotos_validas)
    bytes_list, nombres = [], []
    for i, foto in enumerate(fotos_validas, 1):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f"MAT_{id_servicio}_{ts}_f{i}.jpg"
        nombres.append(fname)
        bytes_list.append((foto.read(), fname))

    data = {
        'FECHA_REGISTRO': fecha_reg,
        'ID_SERVICIO':    id_servicio,
        'TIPO_ACCION':    tipo_accion,
        'OPERADOR':       operador,
        'MATERIALES':     materiales_str,
        'CANT_FOTOS':     cant_fotos,
        'FOTOS':          '|'.join(nombres),
        'FOTO_ORIGEN':    request.form.get('foto_origen', ''),
        'OBSERVACION':    observacion,
        'LATITUD':        request.form.get('latitud', ''),
        'LONGITUD':       request.form.get('longitud', ''),
    }
    df_m = pd.DataFrame([data])
    if os.path.exists(MAT_USADOS_PATH):
        df_m.to_csv(MAT_USADOS_PATH, mode='a', header=False, index=False, sep=';')
    else:
        df_m.to_csv(MAT_USADOS_PATH, index=False, sep=';')

    if bytes_list:
        procesar_fotos_async(bytes_list, f"MAT-{id_servicio}", FOTOS_MATERIALES_FOLDER)

    return render_template('confirmacion_materiales.html',
                           id_servicio=id_servicio,
                           tipo_accion=tipo_accion,
                           operador=operador)



# ─── Buscar Geo ───────────────────────────────────────────────────────────────

@app.route('/geo')
@login_requerido
def geo():
    id_servicio = request.args.get('id_servicio', '').strip()
    resultado   = None
    buscado     = bool(id_servicio)

    if id_servicio:
        resultado = get_geo_index().get(id_servicio)

    return render_template('geo.html',
                           id_servicio=id_servicio,
                           resultado=resultado,
                           buscado=buscado,
                           usuario=usuario_actual())


# ─── Combustible ─────────────────────────────────────────────────────────────

@app.route('/combustible')
@login_requerido
def combustible():
    return render_template('combustible.html', operadores=get_operadores(),
                           usuario=usuario_actual())


@app.route('/combustible/registrar', methods=['POST'])
@login_requerido
def registrar_combustible():
    usuario = usuario_actual()
    operador   = request.form.get('operador', '')
    if not puede_ver_todo(usuario):
        operador = usuario['valor']
    patente    = request.form.get('patente', '').upper()
    km         = request.form.get('km', '')
    num_factura = request.form.get('num_factura', '')
    litros     = request.form.get('litros', '')
    observacion = request.form.get('observacion', '')
    fecha_reg  = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    bytes_list = []
    nombres = {}
    for campo in ['foto_factura', 'foto_odometro', 'foto_vale']:
        # Tomar el primero con archivo entre los dos inputs del campo
        inputs = request.files.getlist(campo)
        foto = next((f for f in inputs if f and f.filename), None)
        if foto:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            fname = f"COMB_{patente}_{campo}_{ts}.jpg"
            nombres[campo] = fname
            bytes_list.append((foto.read(), fname))
        else:
            nombres[campo] = ''

    data = {
        'FECHA_REGISTRO':  fecha_reg,
        'OPERADOR':        operador,
        'PATENTE':         patente,
        'KM':              km,
        'NUM_FACTURA':     num_factura,
        'LITROS':          litros,
        'FOTO_FACTURA':    nombres.get('foto_factura', ''),
        'FOTO_ODOMETRO':   nombres.get('foto_odometro', ''),
        'FOTO_VALE':       nombres.get('foto_vale', ''),
        'OBSERVACION':     observacion,
        'LATITUD':         request.form.get('latitud', ''),
        'LONGITUD':        request.form.get('longitud', ''),
    }
    df_c = pd.DataFrame([data])
    if os.path.exists(COMBUSTIBLE_PATH):
        df_c.to_csv(COMBUSTIBLE_PATH, mode='a', header=False, index=False, sep=';')
    else:
        df_c.to_csv(COMBUSTIBLE_PATH, index=False, sep=';')

    if bytes_list:
        procesar_fotos_async(bytes_list, f"COMB-{patente}", FOTOS_COMBUSTIBLE_FOLDER)

    return render_template('confirmacion_combustible.html',
                           operador=operador, patente=patente,
                           km=km, litros=litros)


# ─── Caja Chica ──────────────────────────────────────────────────────────────

@app.route('/caja-chica')
@acceso_caja_chica
def caja_chica():
    usuario = usuario_actual()
    df = get_caja_chica()
    if not es_direccion(usuario):
        df = df[df['SOLICITANTE'] == usuario['valor']]
    if not df.empty:
        df = df.sort_values('ID', key=lambda s: s.astype(int), ascending=False)
    solicitudes = df.to_dict('records')
    return render_template('caja_chica.html',
                           categorias=CAJA_CHICA_CATEGORIAS,
                           solicitudes=solicitudes,
                           usuario=usuario)


@app.route('/caja-chica/solicitar', methods=['POST'])
@acceso_caja_chica
def caja_chica_solicitar():
    usuario = usuario_actual()
    df = get_caja_chica()
    fila = {col: '' for col in CAJA_CHICA_COLUMNS}
    fila.update({
        'ID':               _next_caja_chica_id(df),
        'FECHA_SOLICITUD':  datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'SOLICITANTE':      usuario['valor'],
        'CATEGORIA':        request.form.get('categoria', ''),
        'DESCRIPCION':      request.form.get('descripcion', ''),
        'MONTO_SOLICITADO': request.form.get('monto_solicitado', ''),
        'ESTADO':           'PENDIENTE',
    })
    df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    guardar_caja_chica(df)
    return redirect(url_for('caja_chica'))


@app.route('/admin/caja-chica/aprobar/<id_sol>', methods=['POST'])
def caja_chica_aprobar(id_sol):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    df = get_caja_chica()
    idx = df.index[df['ID'] == id_sol]
    if len(idx):
        df.loc[idx, 'ESTADO'] = 'APROBADA'
        df.loc[idx, 'FECHA_APROBACION'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        guardar_caja_chica(df)
    return redirect(url_for('admin'))


@app.route('/admin/caja-chica/rechazar/<id_sol>', methods=['POST'])
def caja_chica_rechazar(id_sol):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    df = get_caja_chica()
    idx = df.index[df['ID'] == id_sol]
    if len(idx):
        df.loc[idx, 'ESTADO'] = 'RECHAZADA'
        df.loc[idx, 'FECHA_APROBACION'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        df.loc[idx, 'COMENTARIO_APROBACION'] = request.form.get('comentario', '')
        guardar_caja_chica(df)
    return redirect(url_for('admin'))


@app.route('/caja-chica/rendir/<id_sol>')
@acceso_caja_chica
def caja_chica_rendir_form(id_sol):
    usuario = usuario_actual()
    df = get_caja_chica()
    row = df[df['ID'] == id_sol]
    if row.empty or row.iloc[0]['ESTADO'] != 'APROBADA' or row.iloc[0]['SOLICITANTE'] != usuario['valor']:
        return redirect(url_for('caja_chica'))
    return render_template('caja_chica_rendir.html',
                           solicitud=row.iloc[0].to_dict(),
                           tipos_doc=CAJA_CHICA_TIPOS_DOC)


@app.route('/caja-chica/rendir/<id_sol>', methods=['POST'])
@acceso_caja_chica
def caja_chica_rendir(id_sol):
    usuario = usuario_actual()
    df = get_caja_chica()
    idx = df.index[df['ID'] == id_sol]
    if not len(idx) or df.loc[idx[0], 'ESTADO'] != 'APROBADA' or df.loc[idx[0], 'SOLICITANTE'] != usuario['valor']:
        return redirect(url_for('caja_chica'))

    foto = request.files.get('foto_documento')
    fname = ''
    if foto and foto.filename:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f"CC_{id_sol}_{ts}.jpg"
        procesar_fotos_async([(foto.read(), fname)], f"CC-{id_sol}", FOTOS_CAJA_CHICA_FOLDER)

    df.loc[idx, 'TIPO_DOCUMENTO']  = request.form.get('tipo_documento', '')
    df.loc[idx, 'NUM_DOCUMENTO']   = request.form.get('num_documento', '')
    df.loc[idx, 'RUT_PROVEEDOR']   = request.form.get('rut_proveedor', '')
    df.loc[idx, 'RAZON_SOCIAL']    = request.form.get('razon_social', '')
    df.loc[idx, 'MONTO_NETO']      = request.form.get('monto_neto', '')
    df.loc[idx, 'IVA']             = request.form.get('iva', '')
    df.loc[idx, 'MONTO_TOTAL']     = request.form.get('monto_total', '')
    df.loc[idx, 'FOTO_DOCUMENTO']  = fname
    df.loc[idx, 'FECHA_RENDICION'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    df.loc[idx, 'ESTADO']          = 'RENDIDA'
    df.loc[idx, 'LATITUD']         = request.form.get('latitud', '')
    df.loc[idx, 'LONGITUD']        = request.form.get('longitud', '')
    guardar_caja_chica(df)

    solicitud = df.loc[idx[0]].to_dict()
    return render_template('confirmacion_caja_chica.html', solicitud=solicitud)


# ─── Descargas ───────────────────────────────────────────────────────────────

@app.route('/descargar/resultados')
def descargar_resultados():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if not os.path.exists(RESULTADOS_PATH):
        return "Sin resultados aún.", 404
    return send_file(RESULTADOS_PATH, as_attachment=True,
                     download_name=f"resultados_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/descargar/consolidado')
def descargar_consolidado():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    df_c = get_df()
    df_r = get_resultados()
    if df_c is None:
        return "Sin clientes cargados.", 404
    merged = df_c.merge(df_r, on='ID_SERVICIO', how='left') if not df_r.empty else df_c.copy()
    tmp = os.path.join(DATA_FOLDER, 'consolidado_tmp.csv')
    merged.to_csv(tmp, index=False, encoding='utf-8-sig', sep=';')
    return send_file(tmp, as_attachment=True,
                     download_name=f"consolidado_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/descargar/materiales-usados')
def descargar_materiales_usados():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if not os.path.exists(MAT_USADOS_PATH):
        return "Sin registros de materiales aún.", 404
    return send_file(MAT_USADOS_PATH, as_attachment=True,
                     download_name=f"materiales_usados_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/descargar/ejemplo')
def descargar_ejemplo():
    import io
    contenido = (
        "ID_SERVICIO;FECHA_CORTE;DEUDA;ANTIGUEDAD;TIPO CORTE;OPERADOR;DIRECCION;MEDIDOR;LOCALIDAD;PAGO\n"
        "100001;01/01/2026;85000;2;LLAVE DE PASO;JUAN PEREZ;AV. ARTURO PRAT 123;M-000123;IQUIQUE;0\n"
    )
    buffer = io.BytesIO(contenido.encode('utf-8-sig'))
    return send_file(buffer, as_attachment=True,
                     download_name='ejemplo_clientes.csv', mimetype='text/csv')


@app.route('/descargar/combustible')
def descargar_combustible():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if not os.path.exists(COMBUSTIBLE_PATH):
        return "Sin registros de combustible aún.", 404
    return send_file(COMBUSTIBLE_PATH, as_attachment=True,
                     download_name=f"combustible_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/descargar/caja-chica')
def descargar_caja_chica():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    if not os.path.exists(CAJA_CHICA_PATH):
        return "Sin registros de caja chica aún.", 404
    return send_file(CAJA_CHICA_PATH, as_attachment=True,
                     download_name=f"caja_chica_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/sw.js')
def sw():
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)