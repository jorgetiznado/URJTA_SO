"""
asistencia.py
=============
Lógica de la nómina de asistencia por QR (sin dependencias de Flask ni pandas, para
poder probarla sola: `python test_asistencia.py`).

Cómo funciona el marcaje en terreno
-----------------------------------
1. El supervisor abre `/asistencia/qr` en el punto de reunión (teléfono, tablet o PC).
   La pantalla muestra un QR que **cambia cada 30 segundos**.
2. El trabajador lo escanea con la cámara de su teléfono — el QR contiene la URL
   `/asistencia/marcar?t=<token>` del propio sistema.
3. El token va firmado (HMAC-SHA256 con `URJTA_SECRET_KEY`) y lleva la ventana de tiempo
   en que fue emitido: solo se acepta durante ~90 segundos. Una foto del QR mandada por
   WhatsApp llega vencida, así que no se puede marcar desde la casa.
4. La hora del marcaje la pone el servidor, nunca el teléfono. El GPS del teléfono se
   guarda como respaldo (referencial: el navegador lo entrega solo si el usuario acepta).

Para quien no anda con smartphone existe la **credencial**: un QR fijo por trabajador
(`/asistencia/credenciales`, imprimible) que el supervisor escanea desde su propio
teléfono en `/asistencia/escanear`. También va firmado, para que nadie se imprima una
credencial con el código de otro.

La nómina del día no se guarda: se calcula a partir de los marcajes (`asistencia.csv`),
la lista de trabajadores activos (`operadores.csv`) y las justificaciones de ausencia
(`asistencia_justificaciones.csv`). Así nunca queda desincronizada.
"""

import base64
import hashlib
import hmac
import time
from datetime import datetime

# ─── Formato y constantes ────────────────────────────────────────────────────

FORMATO_FECHA = '%d/%m/%Y'
FORMATO_HORA  = '%H:%M:%S'

# El QR de jornada rota cada VENTANA_SEGUNDOS y se aceptan VENTANAS_TOLERADAS
# ventanas anteriores, para que alcance a marcar quien escaneó justo en el cambio.
VENTANA_SEGUNDOS   = 30
VENTANAS_TOLERADAS = 2

# Marcajes idénticos seguidos (doble escaneo por nervios) se descartan dentro de este lapso.
MINUTOS_ANTIREBOTE = 2

TIPO_ENTRADA = 'ENTRADA'
TIPO_SALIDA  = 'SALIDA'

ORIGEN_QR         = 'QR_JORNADA'
ORIGEN_CREDENCIAL = 'CREDENCIAL'
ORIGEN_MANUAL     = 'MANUAL'

ASISTENCIA_COLUMNS = [
    'ID', 'FECHA', 'HORA', 'TIPO', 'CODIGO', 'NOMBRE', 'CARGO',
    'ORIGEN', 'PUNTO', 'LATITUD', 'LONGITUD', 'REGISTRADO_POR', 'OBSERVACION',
]

JUSTIFICACION_COLUMNS = [
    'FECHA', 'CODIGO', 'NOMBRE', 'MOTIVO', 'COMENTARIO', 'REGISTRADO_POR', 'FECHA_REGISTRO',
]

MOTIVOS_JUSTIFICACION = [
    'LICENCIA MÉDICA',
    'VACACIONES',
    'PERMISO CON GOCE',
    'PERMISO SIN GOCE',
    'DÍA ADMINISTRATIVO',
    'CAPACITACIÓN',
    'DESCANSO / TURNO LIBRE',
    'FALTA INJUSTIFICADA',
]

# Estados posibles de una fila de la nómina.
ESTADO_PRESENTE    = 'PRESENTE'
ESTADO_ATRASO      = 'ATRASO'
ESTADO_AUSENTE     = 'AUSENTE'
ESTADO_JUSTIFICADO = 'JUSTIFICADO'
ESTADO_NO_LABORAL  = 'NO LABORAL'


# ─── Token del QR de jornada ─────────────────────────────────────────────────

def _b64(texto):
    return base64.urlsafe_b64encode(texto.encode('utf-8')).decode('ascii').rstrip('=')


def _desde_b64(texto):
    relleno = '=' * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno).decode('utf-8')


def _firma(mensaje, secreto):
    return hmac.new(secreto.encode('utf-8'), mensaje.encode('utf-8'), hashlib.sha256).hexdigest()[:12]


def ventana_actual(ahora=None):
    """Número de ventana de 30 s en que estamos (lo que hace rotar el QR)."""
    return int((time.time() if ahora is None else ahora) // VENTANA_SEGUNDOS)


def token_jornada(punto, secreto, ahora=None):
    """Token firmado que viaja dentro del QR de jornada: `<punto>.<ventana>.<firma>`."""
    base = f"{_b64(punto)}.{ventana_actual(ahora)}"
    return f"{base}.{_firma(base, secreto)}"


def validar_token(token, secreto, ahora=None):
    """Valida el token del QR de jornada.

    Devuelve `(punto, None)` si es válido, o `(None, motivo)` con un mensaje
    en castellano listo para mostrarle al trabajador.
    """
    partes = str(token or '').split('.')
    if len(partes) != 3:
        return None, 'El código QR no es válido. Pídele al supervisor que muestre el QR de jornada.'

    punto_codificado, ventana_texto, firma = partes
    base = f"{punto_codificado}.{ventana_texto}"
    if not hmac.compare_digest(firma, _firma(base, secreto)):
        return None, 'El código QR no es válido o fue alterado.'

    try:
        ventana = int(ventana_texto)
        punto = _desde_b64(punto_codificado)
    except (ValueError, UnicodeDecodeError):
        return None, 'El código QR no es válido.'

    diferencia = ventana_actual(ahora) - ventana
    if diferencia < 0:
        return None, 'El código QR viene de un reloj adelantado. Avisa al supervisor.'
    if diferencia > VENTANAS_TOLERADAS:
        segundos = VENTANA_SEGUNDOS * (VENTANAS_TOLERADAS + 1)
        return None, (f'Este código QR ya venció (dura {segundos} segundos). '
                      f'Escanea de nuevo el QR que está en pantalla.')

    return punto, None


# ─── Credencial QR por trabajador ────────────────────────────────────────────

PREFIJO_CREDENCIAL = 'URJTA-AST'


def credencial_qr(codigo, secreto):
    """Contenido del QR fijo de la credencial de un trabajador (no caduca)."""
    codigo = str(codigo).strip()
    return f"{PREFIJO_CREDENCIAL}:{codigo}:{_firma(f'{PREFIJO_CREDENCIAL}:{codigo}', secreto)}"


def validar_credencial(contenido, secreto):
    """Devuelve `(codigo, None)` si la credencial es legítima, o `(None, motivo)`."""
    partes = str(contenido or '').strip().split(':')
    if len(partes) != 3 or partes[0] != PREFIJO_CREDENCIAL:
        return None, 'Ese QR no es una credencial de asistencia URJTA.'
    _, codigo, firma = partes
    if not hmac.compare_digest(firma, _firma(f'{PREFIJO_CREDENCIAL}:{codigo}', secreto)):
        return None, 'La credencial no es válida o fue alterada.'
    return codigo, None


# ─── Cálculo de la jornada ───────────────────────────────────────────────────

def _a_minutos(hora):
    """'08:35:12' -> 515 minutos desde medianoche. None si no se puede leer."""
    try:
        partes = [int(p) for p in str(hora).strip().split(':')]
    except ValueError:
        return None
    if len(partes) < 2:
        return None
    return partes[0] * 60 + partes[1]


def hhmm(minutos):
    """515 -> '08:35'. Sirve tanto para horas del día como para duraciones."""
    if minutos is None:
        return ''
    return f"{int(minutos) // 60:02d}:{int(minutos) % 60:02d}"


def _ordenadas(marcas):
    return sorted(marcas, key=lambda m: str(m.get('HORA', '')))


def siguiente_tipo(marcas_del_dia):
    """Qué corresponde marcar ahora: la primera marca del día es ENTRADA y desde
    ahí se van alternando (permite varias entradas/salidas: colación, otro frente)."""
    previas = _ordenadas(marcas_del_dia)
    if not previas:
        return TIPO_ENTRADA
    return TIPO_SALIDA if previas[-1].get('TIPO') == TIPO_ENTRADA else TIPO_ENTRADA


def marca_reciente(marcas_del_dia, hora_actual):
    """Devuelve el último marcaje si ocurrió hace menos de MINUTOS_ANTIREBOTE, o None.

    Sirve para descartar el doble escaneo: quien toca dos veces el botón no debe
    quedar con una ENTRADA y una SALIDA seguidas (jornada de cero minutos).
    """
    ahora = _a_minutos(hora_actual)
    if ahora is None:
        return None
    previas = _ordenadas(marcas_del_dia)
    if not previas:
        return None
    ultima = previas[-1]
    previo = _a_minutos(ultima.get('HORA'))
    if previo is not None and 0 <= ahora - previo <= MINUTOS_ANTIREBOTE:
        return ultima
    return None


def minutos_trabajados(marcas_del_dia):
    """Suma los tramos ENTRADA→SALIDA del día. Una ENTRADA sin su SALIDA queda abierta
    (no se cuenta: la jornada todavía no cierra)."""
    total = 0
    abierta = None
    for marca in _ordenadas(marcas_del_dia):
        minuto = _a_minutos(marca.get('HORA'))
        if minuto is None:
            continue
        if marca.get('TIPO') == TIPO_ENTRADA:
            if abierta is None:
                abierta = minuto
        elif abierta is not None:
            total += max(0, minuto - abierta)
            abierta = None
    return total, abierta is not None


def resumen_persona(marcas_del_dia, hora_entrada='08:30', tolerancia_min=10,
                    justificacion=None, dia_laboral=True):
    """Una fila de la nómina para un trabajador en un día."""
    marcas = _ordenadas(marcas_del_dia)
    entradas = [m for m in marcas if m.get('TIPO') == TIPO_ENTRADA]
    salidas  = [m for m in marcas if m.get('TIPO') == TIPO_SALIDA]

    trabajados, jornada_abierta = minutos_trabajados(marcas)
    fila = {
        'ENTRADA':         entradas[0].get('HORA', '')[:5] if entradas else '',
        'SALIDA':          salidas[-1].get('HORA', '')[:5] if salidas else '',
        'MARCAS':          len(marcas),
        'MINUTOS':         trabajados,
        'HORAS':           hhmm(trabajados) if trabajados else '',
        'JORNADA_ABIERTA': jornada_abierta,
        'ATRASO_MIN':      0,
        'ORIGEN':          entradas[0].get('ORIGEN', '') if entradas else '',
        'MOTIVO':          (justificacion or {}).get('MOTIVO', ''),
        'COMENTARIO':      (justificacion or {}).get('COMENTARIO', ''),
    }

    if marcas:
        inicio_esperado = _a_minutos(hora_entrada)
        llegada = _a_minutos(entradas[0].get('HORA')) if entradas else None
        if inicio_esperado is not None and llegada is not None:
            fila['ATRASO_MIN'] = max(0, llegada - inicio_esperado - int(tolerancia_min))
        fila['ESTADO'] = ESTADO_ATRASO if fila['ATRASO_MIN'] > 0 else ESTADO_PRESENTE
    elif justificacion:
        fila['ESTADO'] = ESTADO_JUSTIFICADO
    elif not dia_laboral:
        fila['ESTADO'] = ESTADO_NO_LABORAL
    else:
        fila['ESTADO'] = ESTADO_AUSENTE

    return fila


def construir_nomina(trabajadores, marcas, justificaciones, fecha,
                     hora_entrada='08:30', tolerancia_min=10, dia_laboral=True):
    """Nómina completa de un día: una fila por trabajador activo, esté o no presente.

    - `trabajadores`: dicts con CODIGO, NOMBRE, CARGO (operadores.csv ya filtrado).
    - `marcas`: marcajes de esa fecha (dicts con CODIGO, TIPO, HORA, ORIGEN...).
    - `justificaciones`: dicts con CODIGO, MOTIVO, COMENTARIO de esa fecha.
    """
    por_codigo = {}
    for marca in marcas:
        if str(marca.get('FECHA', fecha)).strip() == fecha:
            por_codigo.setdefault(str(marca.get('CODIGO', '')).strip(), []).append(marca)

    justificado = {
        str(j.get('CODIGO', '')).strip(): j
        for j in justificaciones if str(j.get('FECHA', '')).strip() == fecha
    }

    nomina = []
    for trabajador in trabajadores:
        codigo = str(trabajador.get('CODIGO', '')).strip()
        fila = {
            'CODIGO': codigo,
            'NOMBRE': trabajador.get('NOMBRE', ''),
            'CARGO':  trabajador.get('CARGO', ''),
            'FECHA':  fecha,
        }
        fila.update(resumen_persona(
            por_codigo.get(codigo, []), hora_entrada, tolerancia_min,
            justificado.get(codigo), dia_laboral,
        ))
        nomina.append(fila)

    # Marcajes de gente que ya no está en la lista de operadores activos: se muestran
    # igual, para que la nómina no esconda un marcaje real.
    conocidos = {str(t.get('CODIGO', '')).strip() for t in trabajadores}
    for codigo, marcas_persona in por_codigo.items():
        if codigo in conocidos:
            continue
        fila = {
            'CODIGO': codigo,
            'NOMBRE': marcas_persona[0].get('NOMBRE', codigo),
            'CARGO':  marcas_persona[0].get('CARGO', ''),
            'FECHA':  fecha,
        }
        fila.update(resumen_persona(marcas_persona, hora_entrada, tolerancia_min, None, dia_laboral))
        nomina.append(fila)

    orden_estado = {ESTADO_ATRASO: 0, ESTADO_PRESENTE: 1, ESTADO_AUSENTE: 2,
                    ESTADO_JUSTIFICADO: 3, ESTADO_NO_LABORAL: 4}
    nomina.sort(key=lambda f: (orden_estado.get(f['ESTADO'], 9), str(f['NOMBRE']).upper()))
    return nomina


def totales_nomina(nomina):
    """KPIs del encabezado de la nómina."""
    minutos = sum(f['MINUTOS'] for f in nomina)
    return {
        'dotacion':     len(nomina),
        'presentes':    sum(1 for f in nomina if f['ESTADO'] in (ESTADO_PRESENTE, ESTADO_ATRASO)),
        'atrasos':      sum(1 for f in nomina if f['ESTADO'] == ESTADO_ATRASO),
        'ausentes':     sum(1 for f in nomina if f['ESTADO'] == ESTADO_AUSENTE),
        'justificados': sum(1 for f in nomina if f['ESTADO'] == ESTADO_JUSTIFICADO),
        'abiertas':     sum(1 for f in nomina if f['JORNADA_ABIERTA']),
        'horas_total':  hhmm(minutos),
        'minutos_total': minutos,
    }


def es_dia_laboral(fecha_texto, dias_habiles):
    """`dias_habiles`: iterable con días de la semana (1=lunes ... 7=domingo)."""
    try:
        fecha = datetime.strptime(fecha_texto, FORMATO_FECHA)
    except (ValueError, TypeError):
        return True
    return fecha.isoweekday() in set(dias_habiles)
