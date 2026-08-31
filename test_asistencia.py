"""
test_asistencia.py
==================
Pruebas de la lógica de asistencia. Se corren solas, sin dependencias:

    python test_asistencia.py

(También las toma `pytest` si algún día se agrega al proyecto.)
"""

import asistencia as a

SECRETO = 'clave-de-prueba-larga'


# ─── Token del QR de jornada ─────────────────────────────────────────────────

def test_token_valido_en_su_ventana():
    ahora = 1_800_000_000
    token = a.token_jornada('BASE IQUIQUE', SECRETO, ahora=ahora)
    punto, error = a.validar_token(token, SECRETO, ahora=ahora)
    assert error is None
    assert punto == 'BASE IQUIQUE'


def test_token_sobrevive_la_ventana_de_gracia():
    ahora = 1_800_000_000
    token = a.token_jornada('BASE', SECRETO, ahora=ahora)
    # 60 s después (2 ventanas) todavía sirve: alcanzó a escanear en el cambio.
    punto, error = a.validar_token(token, SECRETO, ahora=ahora + 60)
    assert error is None and punto == 'BASE'


def test_token_vencido_se_rechaza():
    ahora = 1_800_000_000
    token = a.token_jornada('BASE', SECRETO, ahora=ahora)
    # 5 minutos después (la foto del QR mandada por WhatsApp).
    punto, error = a.validar_token(token, SECRETO, ahora=ahora + 300)
    assert punto is None and 'venció' in error


def test_token_con_firma_alterada_se_rechaza():
    ahora = 1_800_000_000
    token = a.token_jornada('BASE', SECRETO, ahora=ahora)
    cuerpo, _, _firma = token.rpartition('.')
    punto, error = a.validar_token(f"{cuerpo}.000000000000", SECRETO, ahora=ahora)
    assert punto is None and error


def test_token_de_otro_secreto_se_rechaza():
    ahora = 1_800_000_000
    token = a.token_jornada('BASE', 'otro-secreto', ahora=ahora)
    punto, error = a.validar_token(token, SECRETO, ahora=ahora)
    assert punto is None and error


def test_token_basura_no_revienta():
    for basura in ['', None, 'hola', 'a.b', 'a.b.c.d', 'x.y.z']:
        punto, error = a.validar_token(basura, SECRETO)
        assert punto is None and error


# ─── Credencial ──────────────────────────────────────────────────────────────

def test_credencial_ida_y_vuelta():
    qr = a.credencial_qr('1023', SECRETO)
    codigo, error = a.validar_credencial(qr, SECRETO)
    assert error is None and codigo == '1023'


def test_credencial_falsificada_se_rechaza():
    qr = a.credencial_qr('1023', SECRETO)
    falsa = qr.replace(':1023:', ':9999:')
    codigo, error = a.validar_credencial(falsa, SECRETO)
    assert codigo is None and error


def test_credencial_de_otro_sistema_se_rechaza():
    codigo, error = a.validar_credencial('https://algun-sitio.cl', SECRETO)
    assert codigo is None and error


# ─── Alternancia entrada/salida y antirrebote ────────────────────────────────

def _marca(tipo, hora, codigo='1', origen=a.ORIGEN_QR):
    return {'CODIGO': codigo, 'TIPO': tipo, 'HORA': hora, 'ORIGEN': origen,
            'FECHA': '01/09/2026', 'NOMBRE': 'JUAN PEREZ', 'CARGO': 'OPERADOR'}


def test_primera_marca_del_dia_es_entrada():
    assert a.siguiente_tipo([]) == a.TIPO_ENTRADA


def test_alterna_entrada_y_salida():
    marcas = [_marca(a.TIPO_ENTRADA, '08:00:00')]
    assert a.siguiente_tipo(marcas) == a.TIPO_SALIDA
    marcas.append(_marca(a.TIPO_SALIDA, '13:00:00'))
    assert a.siguiente_tipo(marcas) == a.TIPO_ENTRADA


def test_doble_escaneo_seguido_es_rebote():
    marcas = [_marca(a.TIPO_ENTRADA, '08:00:00')]
    # Tocar dos veces el botón no puede dejar una ENTRADA y una SALIDA seguidas.
    assert a.marca_reciente(marcas, '08:01:30')['TIPO'] == a.TIPO_ENTRADA
    assert a.marca_reciente(marcas, '08:40:00') is None
    assert a.marca_reciente([], '08:00:00') is None


def test_salida_normal_no_es_rebote():
    marcas = [_marca(a.TIPO_ENTRADA, '08:00:00'), _marca(a.TIPO_SALIDA, '18:00:00')]
    assert a.marca_reciente(marcas, '18:05:00') is None


# ─── Horas trabajadas ────────────────────────────────────────────────────────

def test_suma_tramos_con_colacion():
    marcas = [
        _marca(a.TIPO_ENTRADA, '08:00:00'),
        _marca(a.TIPO_SALIDA,  '13:00:00'),
        _marca(a.TIPO_ENTRADA, '14:00:00'),
        _marca(a.TIPO_SALIDA,  '18:30:00'),
    ]
    minutos, abierta = a.minutos_trabajados(marcas)
    assert minutos == 5 * 60 + 4 * 60 + 30
    assert abierta is False
    assert a.hhmm(minutos) == '09:30'


def test_jornada_sin_salida_queda_abierta():
    minutos, abierta = a.minutos_trabajados([_marca(a.TIPO_ENTRADA, '08:00:00')])
    assert minutos == 0 and abierta is True


def test_marcas_desordenadas_se_ordenan_por_hora():
    marcas = [_marca(a.TIPO_SALIDA, '18:00:00'), _marca(a.TIPO_ENTRADA, '08:00:00')]
    minutos, abierta = a.minutos_trabajados(marcas)
    assert minutos == 600 and abierta is False


# ─── Nómina del día ──────────────────────────────────────────────────────────

TRABAJADORES = [
    {'CODIGO': '1', 'NOMBRE': 'JUAN PEREZ',   'CARGO': 'OPERADOR'},
    {'CODIGO': '2', 'NOMBRE': 'ANA SOTO',     'CARGO': 'OPERADOR'},
    {'CODIGO': '3', 'NOMBRE': 'LUIS ROJAS',   'CARGO': 'SUPERVISOR'},
    {'CODIGO': '4', 'NOMBRE': 'MARTA DIAZ',   'CARGO': 'ADMINISTRATIVO'},
]
FECHA = '01/09/2026'


def _nomina(marcas, justificaciones=()):
    return {f['CODIGO']: f for f in a.construir_nomina(
        TRABAJADORES, marcas, list(justificaciones), FECHA,
        hora_entrada='08:30', tolerancia_min=10)}


def test_nomina_clasifica_los_cuatro_estados():
    marcas = [
        _marca(a.TIPO_ENTRADA, '08:25:00', codigo='1'),
        _marca(a.TIPO_SALIDA,  '18:00:00', codigo='1'),
        _marca(a.TIPO_ENTRADA, '09:05:00', codigo='2'),   # 25 min de atraso neto
    ]
    justificaciones = [{'FECHA': FECHA, 'CODIGO': '3', 'MOTIVO': 'VACACIONES', 'COMENTARIO': ''}]
    filas = _nomina(marcas, justificaciones)

    assert filas['1']['ESTADO'] == a.ESTADO_PRESENTE
    assert filas['1']['ENTRADA'] == '08:25' and filas['1']['SALIDA'] == '18:00'
    assert filas['1']['HORAS'] == '09:35'

    assert filas['2']['ESTADO'] == a.ESTADO_ATRASO
    assert filas['2']['ATRASO_MIN'] == 25
    assert filas['2']['JORNADA_ABIERTA'] is True

    assert filas['3']['ESTADO'] == a.ESTADO_JUSTIFICADO
    assert filas['3']['MOTIVO'] == 'VACACIONES'

    assert filas['4']['ESTADO'] == a.ESTADO_AUSENTE


def test_tolerancia_no_marca_atraso():
    # 08:38 con entrada 08:30 y 10 min de tolerancia: llega justo, no es atraso.
    filas = _nomina([_marca(a.TIPO_ENTRADA, '08:38:00', codigo='1')])
    assert filas['1']['ESTADO'] == a.ESTADO_PRESENTE
    assert filas['1']['ATRASO_MIN'] == 0


def test_dia_no_laboral_no_deja_ausentes():
    nomina = a.construir_nomina(TRABAJADORES, [], [], FECHA, dia_laboral=False)
    assert all(f['ESTADO'] == a.ESTADO_NO_LABORAL for f in nomina)


def test_marcas_de_otra_fecha_se_ignoran():
    ajena = _marca(a.TIPO_ENTRADA, '08:00:00', codigo='1')
    ajena['FECHA'] = '31/08/2026'
    filas = _nomina([ajena])
    assert filas['1']['ESTADO'] == a.ESTADO_AUSENTE


def test_marca_de_alguien_fuera_de_la_lista_igual_aparece():
    visita = _marca(a.TIPO_ENTRADA, '08:00:00', codigo='99')
    visita['NOMBRE'] = 'PEDRO EXTERNO'
    filas = _nomina([visita])
    assert '99' in filas and filas['99']['NOMBRE'] == 'PEDRO EXTERNO'


def test_totales_cuadran():
    marcas = [
        _marca(a.TIPO_ENTRADA, '08:00:00', codigo='1'),
        _marca(a.TIPO_SALIDA,  '17:00:00', codigo='1'),
        _marca(a.TIPO_ENTRADA, '09:00:00', codigo='2'),
    ]
    nomina = a.construir_nomina(TRABAJADORES, marcas, [], FECHA,
                                hora_entrada='08:30', tolerancia_min=10)
    t = a.totales_nomina(nomina)
    assert t['dotacion'] == 4
    assert t['presentes'] == 2 and t['atrasos'] == 1
    assert t['ausentes'] == 2 and t['abiertas'] == 1
    assert t['horas_total'] == '09:00'


def test_dias_habiles():
    assert a.es_dia_laboral('01/09/2026', [1, 2, 3, 4, 5, 6]) is True    # martes
    assert a.es_dia_laboral('06/09/2026', [1, 2, 3, 4, 5, 6]) is False   # domingo
    assert a.es_dia_laboral('fecha mala', [1]) is True                   # no bloquea


if __name__ == '__main__':
    import sys
    pruebas = [(n, f) for n, f in sorted(globals().items())
               if n.startswith('test_') and callable(f)]
    fallidas = 0
    for nombre, prueba in pruebas:
        try:
            prueba()
            print(f"  ok   {nombre}")
        except AssertionError as e:
            fallidas += 1
            print(f"  FALLA {nombre}: {e or 'assert'}")
        except Exception as e:
            fallidas += 1
            print(f"  ERROR {nombre}: {type(e).__name__}: {e}")
    print(f"\n{len(pruebas) - fallidas}/{len(pruebas)} pruebas OK")
    sys.exit(1 if fallidas else 0)
