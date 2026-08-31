from flask import Flask, render_template, request, redirect, url_for, send_file, session
import pandas as pd
import os
from datetime import datetime, timedelta
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import sync_pipeline
import asistencia


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
ASISTENCIA_PATH      = os.path.join(DATA_FOLDER, 'asistencia.csv')
ASISTENCIA_JUSTIF_PATH = os.path.join(DATA_FOLDER, 'asistencia_justificaciones.csv')

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


# ─── Asistencia (nómina por QR) ──────────────────────────────────────────────
# Todo configurable por .env, para no tocar el código cuando cambie el horario o
# se abra un punto de reunión nuevo.

def _env_int(clave, defecto):
    try:
        return int(str(os.environ.get(clave, defecto)).strip())
    except (TypeError, ValueError):
        return defecto


def _env_lista(clave, defecto):
    return [x.strip() for x in str(os.environ.get(clave, defecto)).split(',') if x.strip()]


ASISTENCIA_HORA_ENTRADA   = os.environ.get('URJTA_ASISTENCIA_HORA_ENTRADA', '08:30').strip()
ASISTENCIA_TOLERANCIA_MIN = _env_int('URJTA_ASISTENCIA_TOLERANCIA_MIN', 10)
ASISTENCIA_PUNTOS         = _env_lista('URJTA_ASISTENCIA_PUNTOS', 'BASE URJTA') or ['BASE URJTA']
# Días hábiles: 1=lunes ... 7=domingo. Por defecto lunes a sábado.
ASISTENCIA_DIAS_HABILES   = [int(d) for d in _env_lista('URJTA_ASISTENCIA_DIAS_HABILES', '1,2,3,4,5,6')
                             if d.isdigit()] or [1, 2, 3, 4, 5, 6]


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


def puede_ver_eerr():
    """EERR visible a Dirección/Gerencia + Administrador de Contrato (o clave admin, transición)."""
    if session.get('admin'):
        return True
    usuario = usuario_actual()
    if not usuario:
        return False
    return es_direccion(usuario) or usuario['cargo'] == CARGO_ADMIN_CONTRATO


def puede_aprobar_caja_chica():
    """Clave única de admin (transición), o Dirección/Gerencia, o quien tenga
    APRUEBA_CAJA_CHICA=SI en operadores.csv (ej. José, sin depender de su cargo)."""
    if session.get('admin'):
        return True
    usuario = usuario_actual()
    if not usuario:
        return False
    if es_direccion(usuario):
        return True
    df = read_csv_safe(OPERADORES_PATH)
    if df is not None and 'APRUEBA_CAJA_CHICA' in df.columns:
        fila = df[df['CODIGO'] == usuario['codigo']]
        if not fila.empty and str(fila.iloc[0]['APRUEBA_CAJA_CHICA']).strip().upper() == 'SI':
            return True
    return False


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('user_codigo'):
            # full_path conserva la query string (ej. el token del QR de asistencia)
            return redirect(url_for('login', next=request.full_path.rstrip('?')))
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



# ─── Asistencia: lectura y escritura ─────────────────────────────────────────

def _hoy():
    return datetime.now().strftime(asistencia.FORMATO_FECHA)


def get_asistencia():
    """Todos los marcajes registrados (texto, sin conversiones)."""
    if not os.path.exists(ASISTENCIA_PATH):
        return pd.DataFrame(columns=asistencia.ASISTENCIA_COLUMNS)
    df = read_csv_safe(ASISTENCIA_PATH)
    if df is None:
        return pd.DataFrame(columns=asistencia.ASISTENCIA_COLUMNS)
    df = df.fillna('')
    for col in asistencia.ASISTENCIA_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    return df[asistencia.ASISTENCIA_COLUMNS]


def get_justificaciones():
    if not os.path.exists(ASISTENCIA_JUSTIF_PATH):
        return pd.DataFrame(columns=asistencia.JUSTIFICACION_COLUMNS)
    df = read_csv_safe(ASISTENCIA_JUSTIF_PATH)
    if df is None:
        return pd.DataFrame(columns=asistencia.JUSTIFICACION_COLUMNS)
    df = df.fillna('')
    for col in asistencia.JUSTIFICACION_COLUMNS:
        if col not in df.columns:
            df[col] = ''
    return df[asistencia.JUSTIFICACION_COLUMNS]


def _agregar_fila_csv(path, fila, columnas):
    """Agrega una fila al final del CSV sin releer ni reescribir el archivo completo.
    Importa para la asistencia: varios trabajadores marcan al mismo tiempo en el
    punto de reunión, y un ciclo leer-modificar-escribir perdería marcajes."""
    df = pd.DataFrame([{col: fila.get(col, '') for col in columnas}])
    if os.path.exists(path):
        df.to_csv(path, mode='a', header=False, index=False, sep=';', encoding='utf-8')
    else:
        df.to_csv(path, index=False, sep=';', encoding='utf-8-sig')


def trabajadores_activos():
    """Dotación que debe aparecer en la nómina (los mismos que pueden iniciar sesión)."""
    return get_operadores_login()


def _trabajador_por_codigo(codigo):
    for trabajador in get_operadores():
        if str(trabajador.get('CODIGO', '')).strip() == str(codigo).strip():
            return trabajador
    return None


def marcas_del_dia(fecha, codigo=None):
    """Marcajes de una fecha ('dd/mm/aaaa'), opcionalmente de un solo trabajador."""
    df = get_asistencia()
    if df.empty:
        return []
    df = df[df['FECHA'].str.strip() == fecha]
    if codigo is not None:
        df = df[df['CODIGO'].str.strip() == str(codigo).strip()]
    return df.to_dict('records')


def puede_gestionar_asistencia():
    """Quién ve el QR de jornada, escanea credenciales y revisa la nómina:
    supervisión, Administrador de Contrato, Dirección/Gerencia — o la clave maestra."""
    return bool(session.get('admin')) or puede_ver_todo(usuario_actual())


def gestion_asistencia_requerida(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if puede_gestionar_asistencia():
            return vista(*args, **kwargs)
        if not session.get('user_codigo'):
            return redirect(url_for('login', next=request.path))
        return render_template('sin_permiso.html'), 403
    return envoltura


def registrar_marca(trabajador, origen, punto='', tipo=None, lat='', lon='',
                    registrado_por='', observacion='', fecha=None, hora=None):
    """Registra un marcaje. Devuelve `(fila, None)` o `(None, motivo)`.

    La fecha y la hora las pone el servidor (el reloj del teléfono no es confiable);
    solo el marcaje manual del supervisor puede fijarlas a mano.
    """
    ahora  = datetime.now()
    fecha  = fecha or ahora.strftime(asistencia.FORMATO_FECHA)
    hora   = hora or ahora.strftime(asistencia.FORMATO_HORA)
    codigo = str(trabajador.get('CODIGO', '')).strip()

    previas = marcas_del_dia(fecha, codigo)
    tipo = tipo or asistencia.siguiente_tipo(previas)

    if origen != asistencia.ORIGEN_MANUAL:
        reciente = asistencia.marca_reciente(previas, hora)
        if reciente:
            return None, (f"Tu {reciente['TIPO'].lower()} de las {reciente['HORA'][:5]} ya quedó "
                          f"registrada. Espera un momento antes de volver a marcar.")

    fila = {
        'ID':             f"{ahora.strftime('%Y%m%d%H%M%S%f')[:-3]}-{codigo}",
        'FECHA':          fecha,
        'HORA':           hora,
        'TIPO':           tipo,
        'CODIGO':         codigo,
        'NOMBRE':         trabajador.get('NOMBRE', ''),
        'CARGO':          str(trabajador.get('CARGO', '')).strip().upper(),
        'ORIGEN':         origen,
        'PUNTO':          punto,
        'LATITUD':        lat,
        'LONGITUD':       lon,
        'REGISTRADO_POR': registrado_por,
        'OBSERVACION':    observacion,
    }
    _agregar_fila_csv(ASISTENCIA_PATH, fila, asistencia.ASISTENCIA_COLUMNS)
    return fila, None


def _hubo_jornada(fecha, marcas):
    """¿Ese día hubo jornada? Es día hábil y alguien marcó.

    Un día hábil en que *nadie* marcó no es un día de 100% de ausencias: es un feriado,
    un día sin faena, o el sistema todavía no estaba en uso. Contarle una falta a toda la
    dotación ensuciaría el cierre de mes. La excepción es hoy: la nómina del día en curso
    tiene que mostrar quién no ha marcado, que es justamente para lo que se mira.
    """
    if not asistencia.es_dia_laboral(fecha, ASISTENCIA_DIAS_HABILES):
        return False
    return bool(marcas) or fecha == _hoy()


def nomina_del_dia(fecha):
    """Nómina completa de un día + sus totales."""
    marcas = marcas_del_dia(fecha)
    nomina = asistencia.construir_nomina(
        trabajadores_activos(),
        marcas,
        get_justificaciones().to_dict('records'),
        fecha,
        hora_entrada=ASISTENCIA_HORA_ENTRADA,
        tolerancia_min=ASISTENCIA_TOLERANCIA_MIN,
        dia_laboral=_hubo_jornada(fecha, marcas),
    )
    return nomina, asistencia.totales_nomina(nomina)


def nomina_rango(desde, hasta):
    """Nómina día por día entre dos fechas (inclusive), para exportar o resumir."""
    try:
        dia   = datetime.strptime(desde, asistencia.FORMATO_FECHA)
        final = datetime.strptime(hasta, asistencia.FORMATO_FECHA)
    except (ValueError, TypeError):
        return []

    trabajadores    = trabajadores_activos()
    justificaciones = get_justificaciones().to_dict('records')
    todas           = get_asistencia().to_dict('records')

    por_fecha = {}
    for marca in todas:
        por_fecha.setdefault(str(marca.get('FECHA', '')).strip(), []).append(marca)

    filas = []
    while dia <= final:
        fecha = dia.strftime(asistencia.FORMATO_FECHA)
        filas.extend(asistencia.construir_nomina(
            trabajadores, por_fecha.get(fecha, []), justificaciones, fecha,
            hora_entrada=ASISTENCIA_HORA_ENTRADA,
            tolerancia_min=ASISTENCIA_TOLERANCIA_MIN,
            dia_laboral=_hubo_jornada(fecha, por_fecha.get(fecha)),
        ))
        dia += timedelta(days=1)
    return filas


def resumen_mensual(fecha_texto):
    """Acumulado del mes hasta la fecha indicada: días trabajados, atrasos, ausencias
    y horas por trabajador. Es lo que se ocupa para cerrar el mes."""
    try:
        referencia = datetime.strptime(fecha_texto, asistencia.FORMATO_FECHA)
    except (ValueError, TypeError):
        return []

    primero = referencia.replace(day=1).strftime(asistencia.FORMATO_FECHA)
    acumulado = {}
    for fila in nomina_rango(primero, fecha_texto):
        resumen = acumulado.setdefault(fila['CODIGO'], {
            'CODIGO': fila['CODIGO'], 'NOMBRE': fila['NOMBRE'], 'CARGO': fila['CARGO'],
            'DIAS': 0, 'ATRASOS': 0, 'AUSENCIAS': 0, 'JUSTIFICADAS': 0,
            'MINUTOS': 0, 'MIN_ATRASO': 0,
        })
        if fila['ESTADO'] in (asistencia.ESTADO_PRESENTE, asistencia.ESTADO_ATRASO):
            resumen['DIAS'] += 1
        if fila['ESTADO'] == asistencia.ESTADO_ATRASO:
            resumen['ATRASOS'] += 1
        if fila['ESTADO'] == asistencia.ESTADO_AUSENTE:
            resumen['AUSENCIAS'] += 1
        if fila['ESTADO'] == asistencia.ESTADO_JUSTIFICADO:
            resumen['JUSTIFICADAS'] += 1
        resumen['MINUTOS']    += fila['MINUTOS']
        resumen['MIN_ATRASO'] += fila['ATRASO_MIN']

    filas = sorted(acumulado.values(), key=lambda r: str(r['NOMBRE']).upper())
    for fila in filas:
        fila['HORAS'] = asistencia.hhmm(fila['MINUTOS'])
        fila['ATRASO_ACUM'] = asistencia.hhmm(fila['MIN_ATRASO'])
    return filas


def qr_svg(datos, escala=9, borde=2, incrustado=False):
    """QR en SVG (nítido en cualquier pantalla y al imprimir). Devuelve `(svg, None)`,
    o `(None, motivo)` si falta la librería en el servidor.

    `incrustado=True` devuelve el SVG sin la cabecera XML, para pegarlo dentro del HTML
    (la hoja de credenciales lleva decenas de QR y así se imprime en una sola página).
    """
    try:
        import segno
    except ImportError:
        return None, ('Falta la librería para generar los QR. En el servidor de URJTA, '
                      'corre: pip install segno')
    codigo = segno.make(datos, error='m')
    if incrustado:
        return codigo.svg_inline(scale=escala, border=borde, dark='#1f1a16'), None
    import io as _io
    buffer = _io.BytesIO()
    codigo.save(buffer, kind='svg', scale=escala, border=borde, dark='#1f1a16')
    return buffer.getvalue().decode('utf-8'), None

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

    _, totales_hoy = nomina_del_dia(datetime.now().strftime(asistencia.FORMATO_FECHA))
    stats['asistencia_presentes'] = totales_hoy['presentes']
    stats['asistencia_dotacion']  = totales_hoy['dotacion']
    stats['asistencia_ausentes']  = totales_hoy['ausentes']

    return render_template('admin_hub.html', stats=stats, error=request.args.get('error'),
                           active_module='inicio', usuario=usuario_actual())


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
                           ultimos=ultimos, error=request.args.get('error'),
                           active_module='clientes', usuario=usuario_actual())


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
                           error=request.args.get('error'),
                           active_module='materiales', usuario=usuario_actual())


@app.route('/admin/combustible')
def admin_combustible_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    df_comb = read_csv_safe(COMBUSTIBLE_PATH) if os.path.exists(COMBUSTIBLE_PATH) else pd.DataFrame()
    stats = {'total_combustible': len(df_comb) if df_comb is not None else 0}
    ultimos_comb = df_comb.tail(10).iloc[::-1].to_dict('records') if df_comb is not None and not df_comb.empty else []

    return render_template('admin_combustible.html', stats=stats, ultimos_comb=ultimos_comb,
                           active_module='combustible', usuario=usuario_actual())


@app.route('/admin/operadores')
def admin_operadores_panel():
    if _admin_requerido():
        return redirect(url_for('admin'))

    operadores = get_operadores()
    stats = {'op_cargado': os.path.exists(OPERADORES_PATH), 'total_operadores': len(operadores)}
    return render_template('admin_operadores.html', stats=stats, operadores=operadores,
                           active_module='operadores', usuario=usuario_actual())


@app.route('/admin/caja-chica')
def admin_caja_chica_panel():
    if not puede_aprobar_caja_chica():
        if not session.get('user_codigo') and not session.get('admin'):
            return redirect(url_for('login', next=request.path))
        return render_template('sin_permiso.html'), 403

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
                           cc_rendidas=cc_rendidas,
                           active_module='caja_chica', usuario=usuario_actual())


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

    eerr = None
    if puede_ver_eerr() and pipeline_disponible:
        try:
            unificado = sync_pipeline.obtener_resumen_unificado()
            eerr = _calcular_eerr(unificado)
        except Exception as e:
            eerr = {'error': str(e)}

    return render_template('admin_cobranza.html', stats=stats,
                           pipeline_disponible=pipeline_disponible,
                           puede_ver_eerr=puede_ver_eerr(), eerr=eerr,
                           active_module='cobranza', usuario=usuario_actual())


def _periodo_de_fecha(serie_fecha):
    return pd.to_datetime(serie_fecha, dayfirst=True, errors='coerce').dt.strftime('%Y%m')


def _calcular_eerr(unificado):
    """Ingresos (EEPP) − Costos (Caja Chica rendida + Combustible) por período,
    más Cortes/Repos/Visitas/Improcedencias del pipeline. Materiales queda
    fuera del costo hasta que tenga campo de precio (integración Defontana
    pendiente — ver placeholder en la plantilla)."""
    if unificado.empty:
        return {'meses': [], 'periodo_actual': None}

    periodos = unificado['PERIODO'].tolist()

    df_cc = get_caja_chica()
    cc_rendida = df_cc[df_cc['ESTADO'] == 'RENDIDA'].copy()
    if not cc_rendida.empty:
        cc_rendida['PERIODO'] = _periodo_de_fecha(cc_rendida['FECHA_RENDICION']).astype('Int64')
        cc_por_periodo = pd.to_numeric(cc_rendida['MONTO_TOTAL'], errors='coerce').fillna(0).groupby(cc_rendida['PERIODO']).sum()
    else:
        cc_por_periodo = pd.Series(dtype=float)

    df_comb = read_csv_safe(COMBUSTIBLE_PATH)
    if df_comb is not None and not df_comb.empty and 'MONTO_VALE' in df_comb.columns:
        df_comb = df_comb.copy()
        df_comb['PERIODO'] = _periodo_de_fecha(df_comb['FECHA_REGISTRO']).astype('Int64')
        comb_por_periodo = pd.to_numeric(df_comb['MONTO_VALE'], errors='coerce').fillna(0).groupby(df_comb['PERIODO']).sum()
    else:
        comb_por_periodo = pd.Series(dtype=float)

    meses = []
    for _, fila in unificado.iterrows():
        p = int(fila['PERIODO'])
        ingreso = float(fila['INGRESO_EEPP'])
        costo_cc = float(cc_por_periodo.get(p, 0) or 0)
        costo_comb = float(comb_por_periodo.get(p, 0) or 0)
        costos = costo_cc + costo_comb
        meses.append({
            'periodo': str(p),
            'cortes': int(fila['CORTES']),
            'repos': int(fila['REPOS']),
            'visitas': int(fila['VISITAS']),
            'improcedencias': int(fila['IMPROCEDENCIAS']),
            'ingreso_eepp': ingreso,
            'costo_caja_chica': costo_cc,
            'costo_combustible': costo_comb,
            'costos_totales': costos,
            'resultado': ingreso - costos,
            'margen_pct': ((ingreso - costos) / ingreso * 100) if ingreso else None,
        })

    return {'meses': meses, 'periodo_actual': str(periodos[-1]) if periodos else None}


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
    monto_vale = request.form.get('monto_vale', '')
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
        'MONTO_VALE':      monto_vale,
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
    if not puede_aprobar_caja_chica():
        return render_template('sin_permiso.html'), 403
    df = get_caja_chica()
    idx = df.index[df['ID'] == id_sol]
    if len(idx):
        df.loc[idx, 'ESTADO'] = 'APROBADA'
        df.loc[idx, 'FECHA_APROBACION'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        guardar_caja_chica(df)
    return redirect(url_for('admin_caja_chica_panel'))


@app.route('/admin/caja-chica/rechazar/<id_sol>', methods=['POST'])
def caja_chica_rechazar(id_sol):
    if not puede_aprobar_caja_chica():
        return render_template('sin_permiso.html'), 403
    df = get_caja_chica()
    idx = df.index[df['ID'] == id_sol]
    if len(idx):
        df.loc[idx, 'ESTADO'] = 'RECHAZADA'
        df.loc[idx, 'FECHA_APROBACION'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        df.loc[idx, 'COMENTARIO_APROBACION'] = request.form.get('comentario', '')
        guardar_caja_chica(df)
    return redirect(url_for('admin_caja_chica_panel'))


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


# ─── Asistencia (nómina por QR) ──────────────────────────────────────────────

def _fecha_pedida():
    """Fecha del parámetro `fecha` (dd/mm/aaaa o aaaa-mm-dd del input date). Hoy por defecto."""
    valor = (request.args.get('fecha') or '').strip()
    for formato in (asistencia.FORMATO_FECHA, '%Y-%m-%d'):
        try:
            return datetime.strptime(valor, formato).strftime(asistencia.FORMATO_FECHA)
        except ValueError:
            continue
    return _hoy()


@app.route('/asistencia')
@login_requerido
def asistencia_inicio():
    """Lo que ve el trabajador: su estado de hoy y su historial del mes."""
    usuario = usuario_actual()
    hoy = _hoy()
    mis_marcas = marcas_del_dia(hoy, usuario['codigo'])
    resumen = asistencia.resumen_persona(mis_marcas, ASISTENCIA_HORA_ENTRADA, ASISTENCIA_TOLERANCIA_MIN)

    primero = datetime.now().replace(day=1).strftime(asistencia.FORMATO_FECHA)
    mi_historial = [f for f in nomina_rango(primero, hoy)
                    if f['CODIGO'] == usuario['codigo'] and f['ESTADO'] != asistencia.ESTADO_NO_LABORAL]
    mi_historial.reverse()

    return render_template(
        'asistencia.html',
        usuario=usuario,
        hoy=hoy,
        marcas=sorted(mis_marcas, key=lambda m: m['HORA']),
        siguiente=asistencia.siguiente_tipo(mis_marcas),
        resumen=resumen,
        historial=mi_historial,
        hora_entrada=ASISTENCIA_HORA_ENTRADA,
        puede_gestionar=puede_gestionar_asistencia(),
    )


@app.route('/asistencia/marcar')
@login_requerido
def asistencia_marcar_form():
    """Pantalla que se abre al escanear el QR de jornada: confirma quién eres y qué marcas."""
    usuario = usuario_actual()
    token = request.args.get('t', '')
    punto, error = asistencia.validar_token(token, app.secret_key)
    mis_marcas = marcas_del_dia(_hoy(), usuario['codigo'])

    return render_template(
        'asistencia_marcar.html',
        usuario=usuario, token=token, punto=punto, error=error,
        tipo=asistencia.siguiente_tipo(mis_marcas),
        marcas=sorted(mis_marcas, key=lambda m: m['HORA']),
        registrada=None,
    )


@app.route('/asistencia/marcar', methods=['POST'])
@login_requerido
def asistencia_marcar():
    usuario = usuario_actual()
    token = request.form.get('token', '')
    punto, error = asistencia.validar_token(token, app.secret_key)

    fila = None
    if not error:
        trabajador = _trabajador_por_codigo(usuario['codigo']) or {
            'CODIGO': usuario['codigo'], 'NOMBRE': usuario['nombre'], 'CARGO': usuario['cargo'],
        }
        fila, error = registrar_marca(
            trabajador,
            origen=asistencia.ORIGEN_QR,
            punto=punto,
            lat=request.form.get('latitud', ''),
            lon=request.form.get('longitud', ''),
        )

    mis_marcas = marcas_del_dia(_hoy(), usuario['codigo'])
    return render_template(
        'asistencia_marcar.html',
        usuario=usuario, token=token, punto=punto, error=error,
        tipo=asistencia.siguiente_tipo(mis_marcas),
        marcas=sorted(mis_marcas, key=lambda m: m['HORA']),
        registrada=fila,
    )


@app.route('/asistencia/qr')
@gestion_asistencia_requerida
def asistencia_qr():
    """Pantalla del punto de reunión: el QR que rota cada 30 segundos."""
    punto = request.args.get('punto', ASISTENCIA_PUNTOS[0])
    if punto not in ASISTENCIA_PUNTOS:
        punto = ASISTENCIA_PUNTOS[0]
    return render_template('asistencia_qr.html', punto=punto, puntos=ASISTENCIA_PUNTOS,
                           ventana=asistencia.VENTANA_SEGUNDOS, usuario=usuario_actual())


@app.route('/asistencia/qr.svg')
@gestion_asistencia_requerida
def asistencia_qr_svg():
    """Imagen del QR vigente. La pantalla la recarga sola antes de que venza."""
    punto = request.args.get('punto', ASISTENCIA_PUNTOS[0])
    if punto not in ASISTENCIA_PUNTOS:
        punto = ASISTENCIA_PUNTOS[0]
    token = asistencia.token_jornada(punto, app.secret_key)
    url = url_for('asistencia_marcar_form', t=token, _external=True)

    svg, error = qr_svg(url, escala=11, borde=2)
    if error:
        return error, 503
    return svg, 200, {'Content-Type': 'image/svg+xml',
                      'Cache-Control': 'no-store, max-age=0'}


@app.route('/asistencia/qr/estado')
@gestion_asistencia_requerida
def asistencia_qr_estado():
    """Contador en vivo de la pantalla del QR: quién va marcando."""
    hoy = _hoy()
    nomina, totales = nomina_del_dia(hoy)
    ultimas = sorted(marcas_del_dia(hoy), key=lambda m: m['HORA'], reverse=True)[:8]
    return {
        'totales': {'dotacion': totales['dotacion'], 'presentes': totales['presentes'],
                    'ausentes': totales['ausentes'], 'atrasos': totales['atrasos']},
        'ultimas': [{'hora': m['HORA'][:5], 'nombre': m['NOMBRE'], 'tipo': m['TIPO']}
                    for m in ultimas],
    }


@app.route('/asistencia/escanear')
@gestion_asistencia_requerida
def asistencia_escanear():
    """Modo supervisor: escanea la credencial del trabajador que no anda con teléfono."""
    return render_template('asistencia_escanear.html',
                           trabajadores=trabajadores_activos(),
                           puntos=ASISTENCIA_PUNTOS,
                           usuario=usuario_actual())


@app.route('/asistencia/escanear/marcar', methods=['POST'])
@gestion_asistencia_requerida
def asistencia_escanear_marcar():
    """Marca por credencial escaneada, o a mano eligiendo al trabajador de la lista."""
    quien = usuario_actual()
    registrado_por = quien['valor'] if quien else 'ADMIN'
    datos = request.get_json(silent=True) or {}
    punto = datos.get('punto', ASISTENCIA_PUNTOS[0])
    contenido = (datos.get('contenido') or '').strip()

    if contenido:
        codigo, error = asistencia.validar_credencial(contenido, app.secret_key)
        origen, observacion = asistencia.ORIGEN_CREDENCIAL, ''
        if error:
            return {'ok': False, 'error': error}
    else:
        codigo = (datos.get('codigo') or '').strip()
        origen = asistencia.ORIGEN_MANUAL
        observacion = (datos.get('observacion') or '').strip()
        if not codigo:
            return {'ok': False, 'error': 'Elige a un trabajador de la lista.'}
        if not observacion:
            return {'ok': False, 'error': 'El marcaje manual necesita un motivo.'}

    trabajador = _trabajador_por_codigo(codigo)
    if not trabajador:
        return {'ok': False, 'error': f'El código {codigo} no está en la lista de operadores.'}

    fila, error = registrar_marca(trabajador, origen=origen, punto=punto,
                                  registrado_por=registrado_por, observacion=observacion)
    if error:
        return {'ok': False, 'error': error, 'nombre': trabajador.get('NOMBRE', '')}
    return {'ok': True, 'nombre': fila['NOMBRE'], 'tipo': fila['TIPO'],
            'hora': fila['HORA'][:5], 'origen': fila['ORIGEN']}


@app.route('/asistencia/credenciales')
@gestion_asistencia_requerida
def asistencia_credenciales():
    """Hoja imprimible con la credencial QR de cada trabajador activo."""
    tarjetas, error = [], None
    for trabajador in trabajadores_activos():
        svg, error = qr_svg(asistencia.credencial_qr(trabajador['CODIGO'], app.secret_key),
                            escala=5, borde=2, incrustado=True)
        if error:
            break
        tarjetas.append({'nombre': trabajador.get('NOMBRE', ''),
                         'codigo': trabajador.get('CODIGO', ''),
                         'cargo':  trabajador.get('CARGO', ''),
                         'svg':    svg})
    return render_template('asistencia_credenciales.html', tarjetas=tarjetas, error=error)


@app.route('/admin/asistencia')
def admin_asistencia_panel():
    """La nómina: todos los trabajadores del día, marquen o no."""
    if not puede_gestionar_asistencia():
        if not session.get('user_codigo') and not session.get('admin'):
            return redirect(url_for('login', next=request.path))
        return render_template('sin_permiso.html'), 403

    fecha = _fecha_pedida()
    nomina, totales = nomina_del_dia(fecha)
    detalle = sorted(marcas_del_dia(fecha), key=lambda m: m['HORA'])

    return render_template(
        'admin_asistencia.html',
        fecha=fecha,
        fecha_iso=datetime.strptime(fecha, asistencia.FORMATO_FECHA).strftime('%Y-%m-%d'),
        es_dia_laboral=asistencia.es_dia_laboral(fecha, ASISTENCIA_DIAS_HABILES),
        nomina=nomina, totales=totales, detalle=detalle,
        resumen_mes=resumen_mensual(fecha),
        trabajadores=trabajadores_activos(),
        motivos=asistencia.MOTIVOS_JUSTIFICACION,
        puntos=ASISTENCIA_PUNTOS,
        hora_entrada=ASISTENCIA_HORA_ENTRADA,
        tolerancia=ASISTENCIA_TOLERANCIA_MIN,
        mensaje=request.args.get('mensaje'), error=request.args.get('error'),
        active_module='asistencia', usuario=usuario_actual(),
    )


@app.route('/admin/asistencia/marcar-manual', methods=['POST'])
def admin_asistencia_marcar_manual():
    """Marcaje a mano cuando algo falló en terreno (teléfono sin batería, sin señal).
    Queda registrado como MANUAL y con el nombre de quien lo hizo."""
    if not puede_gestionar_asistencia():
        return render_template('sin_permiso.html'), 403

    quien = usuario_actual()
    fecha = (request.form.get('fecha') or _hoy()).strip()
    try:
        fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime(asistencia.FORMATO_FECHA)
    except ValueError:
        pass

    trabajador = _trabajador_por_codigo(request.form.get('codigo', ''))
    if not trabajador:
        return redirect(url_for('admin_asistencia_panel', fecha=fecha,
                                error='No se encontró al trabajador.'))

    hora = (request.form.get('hora') or '').strip()
    observacion = (request.form.get('observacion') or '').strip()
    if not observacion:
        return redirect(url_for('admin_asistencia_panel', fecha=fecha,
                                error='El marcaje manual necesita un motivo.'))

    fila, error = registrar_marca(
        trabajador,
        origen=asistencia.ORIGEN_MANUAL,
        punto=request.form.get('punto', ''),
        tipo=request.form.get('tipo') or None,
        registrado_por=quien['valor'] if quien else 'ADMIN',
        observacion=observacion,
        fecha=fecha,
        hora=f"{hora}:00" if len(hora) == 5 else (hora or None),
    )
    if error:
        return redirect(url_for('admin_asistencia_panel', fecha=fecha, error=error))
    return redirect(url_for('admin_asistencia_panel', fecha=fecha,
                            mensaje=f"{fila['TIPO']} manual registrada para {fila['NOMBRE']}."))


@app.route('/admin/asistencia/justificar', methods=['POST'])
def admin_asistencia_justificar():
    """Justifica la ausencia de un trabajador en una fecha (licencia, vacaciones, permiso)."""
    if not puede_gestionar_asistencia():
        return render_template('sin_permiso.html'), 403

    quien = usuario_actual()
    fecha = (request.form.get('fecha') or _hoy()).strip()
    try:
        fecha = datetime.strptime(fecha, '%Y-%m-%d').strftime(asistencia.FORMATO_FECHA)
    except ValueError:
        pass

    trabajador = _trabajador_por_codigo(request.form.get('codigo', ''))
    motivo = request.form.get('motivo', '')
    if not trabajador or not motivo:
        return redirect(url_for('admin_asistencia_panel', fecha=fecha,
                                error='Falta el trabajador o el motivo.'))

    _agregar_fila_csv(ASISTENCIA_JUSTIF_PATH, {
        'FECHA':          fecha,
        'CODIGO':         trabajador['CODIGO'],
        'NOMBRE':         trabajador.get('NOMBRE', ''),
        'MOTIVO':         motivo,
        'COMENTARIO':     request.form.get('comentario', ''),
        'REGISTRADO_POR': quien['valor'] if quien else 'ADMIN',
        'FECHA_REGISTRO': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }, asistencia.JUSTIFICACION_COLUMNS)

    return redirect(url_for('admin_asistencia_panel', fecha=fecha,
                            mensaje=f"Ausencia justificada: {trabajador.get('NOMBRE', '')} — {motivo}."))


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


@app.route('/descargar/asistencia')
def descargar_asistencia():
    """Marcajes en crudo (uno por escaneo), para auditoría."""
    if not puede_gestionar_asistencia():
        return render_template('sin_permiso.html'), 403
    if not os.path.exists(ASISTENCIA_PATH):
        return "Sin marcajes de asistencia aún.", 404
    return send_file(ASISTENCIA_PATH, as_attachment=True,
                     download_name=f"asistencia_{datetime.now().strftime('%Y%m%d')}.csv")


@app.route('/descargar/nomina-asistencia')
def descargar_nomina_asistencia():
    """La nómina consolidada — una fila por trabajador y día, con horas y estado.
    Es el archivo que se ocupa para cerrar el mes (remuneraciones)."""
    if not puede_gestionar_asistencia():
        return render_template('sin_permiso.html'), 403

    hoy = datetime.now()
    desde = (request.args.get('desde') or hoy.replace(day=1).strftime(asistencia.FORMATO_FECHA)).strip()
    hasta = (request.args.get('hasta') or hoy.strftime(asistencia.FORMATO_FECHA)).strip()
    for formato in ('%Y-%m-%d',):
        for nombre, valor in (('desde', desde), ('hasta', hasta)):
            try:
                convertida = datetime.strptime(valor, formato).strftime(asistencia.FORMATO_FECHA)
                if nombre == 'desde':
                    desde = convertida
                else:
                    hasta = convertida
            except ValueError:
                pass

    filas = nomina_rango(desde, hasta)
    if not filas:
        return "Rango de fechas inválido o sin dotación cargada.", 404

    salida = pd.DataFrame([{
        'FECHA':          f['FECHA'],
        'CODIGO':         f['CODIGO'],
        'NOMBRE':         f['NOMBRE'],
        'CARGO':          f['CARGO'],
        'ENTRADA':        f['ENTRADA'],
        'SALIDA':         f['SALIDA'],
        'HORAS':          f['HORAS'],
        'MINUTOS':        f['MINUTOS'],
        'ESTADO':         f['ESTADO'],
        'ATRASO_MIN':     f['ATRASO_MIN'],
        'MARCAS':         f['MARCAS'],
        'ORIGEN_ENTRADA': f['ORIGEN'],
        'MOTIVO':         f['MOTIVO'],
        'COMENTARIO':     f['COMENTARIO'],
    } for f in filas])

    # Se arma en memoria: no deja archivos temporales sueltos ni se pisa a sí mismo
    # si dos personas descargan la nómina al mismo tiempo.
    import io
    buffer = io.BytesIO(salida.to_csv(index=False, sep=';').encode('utf-8-sig'))
    return send_file(buffer, as_attachment=True, mimetype='text/csv',
                     download_name=f"nomina_asistencia_{desde.replace('/', '-')}_a_"
                                   f"{hasta.replace('/', '-')}.csv")


@app.route('/sw.js')
def sw():
    return app.send_static_file('sw.js'), 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)