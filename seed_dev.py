"""
seed_dev.py
===========
Genera datos FICTICIOS en la carpeta de datos para levantar la app en un equipo
de desarrollo (ver README, sección "Desarrollo local").

Existe porque data/ y fotos/ no se versionan: sin esto la app arranca vacía y no
se puede probar ninguna pantalla que dependa de clientes, operadores o rendiciones.

Los datos son inventados — nombres, RUT, direcciones y coordenadas no corresponden
a ningún cliente ni trabajador real. NUNCA correr esto sobre la carpeta de datos
de producción: se niega a sobrescribir archivos que ya existen.

Uso:
    python seed_dev.py
"""

import os

import pandas as pd

DATA_DIR = os.environ.get('URJTA_DATA_DIR', './data')

# Un operador por cargo, para poder probar los cuatro niveles de permiso.
OPERADORES = [
    # CODIGO, NOMBRE,            CARGO,                      ESTADO, APRUEBA_CAJA_CHICA
    ('1001', 'PEREZ JUAN',       'OPERADOR',                 'ACTIVO', ''),
    ('1002', 'ROJAS MARIA',      'OPERADOR',                 'ACTIVO', ''),
    ('2001', 'CASTRO ANDREA',    'SUPERVISOR',               'ACTIVO', ''),
    ('2002', 'MUNOZ CARLOS',     'ADMINISTRATIVO',           'ACTIVO', ''),
    ('3001', 'SOTO PATRICIA',    'ADMINISTRADOR DE CONTRATO', 'ACTIVO', 'SI'),
    ('4001', 'VEGA RICARDO',     'DIRECCION',                'ACTIVO', 'SI'),
]

# OPERADOR va con el nombre pelado (no "codigo - nombre"): viene de RESPONSABLE del
# pipeline, y /campo filtra comparándolo contra el nombre del operador en sesión.
# La última fila queda sin asignar a propósito — es el caso "back office", visible
# solo para los roles que ven todo.
CLIENTES = [
    # ID_SERVICIO, DEUDA, ANTIGUEDAD, TIPO CORTE, OPERADOR, DIRECCION, MEDIDOR, LOCALIDAD
    ('500101', '85400',  '3', 'LLAVE DE PASO',                'PEREZ JUAN',  'AV. LOS AROMOS 1245',   'M-88201', 'OVALLE'),
    ('500102', '132750', '5', 'CANERIA VEREDA SIN PAVIMENTO', 'PEREZ JUAN',  'CALLE EL MOLLE 87',     'M-88202', 'OVALLE'),
    ('500103', '46900',  '2', 'LLAVE DE VEREDA',              'ROJAS MARIA', 'PASAJE SANTA ROSA 340', 'M-88203', 'MONTE PATRIA'),
    ('500104', '210300', '7', 'MATRIZ CON PAVIMENTO',         'ROJAS MARIA', 'AV. LIBERTAD 2210',     'M-88204', 'MONTE PATRIA'),
    ('500105', '67200',  '4', 'LLAVE DE PASO',                '',            'CALLE LAS PALMAS 15',   'M-88205', 'COMBARBALA'),
]

MATERIALES = [
    ('MT-001', 'ABRAZADERA PVC 63MM',        'UN'),
    ('MT-002', 'CANERIA PVC C-10 20MM',      'MT'),
    ('MT-003', 'LLAVE DE PASO 1/2"',         'UN'),
    ('MT-004', 'UNION AMERICANA 1/2"',       'UN'),
    ('MT-005', 'CEMENTO GRIS',               'SC'),
    ('MT-006', 'ARENA',                      'M3'),
]


def _escribir(nombre, df, sep=';'):
    """Escribe un CSV del seed. No pisa archivos existentes — protege datos reales."""
    ruta = os.path.join(DATA_DIR, nombre)
    if os.path.exists(ruta):
        print(f"  = {nombre:24} ya existe, no se toca")
        return
    df.to_csv(ruta, sep=sep, index=False, encoding='utf-8-sig')
    print(f"  + {nombre:24} {len(df)} filas")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Poblando datos ficticios en {os.path.abspath(DATA_DIR)}")

    _escribir('operadores.csv', pd.DataFrame(
        OPERADORES, columns=['CODIGO', 'NOMBRE', 'CARGO', 'ESTADO', 'APRUEBA_CAJA_CHICA']))

    clientes = pd.DataFrame(CLIENTES, columns=[
        'ID_SERVICIO', 'DEUDA', 'ANTIGUEDAD', 'TIPO CORTE', 'OPERADOR',
        'DIRECCION', 'MEDIDOR', 'LOCALIDAD'])
    clientes['FECHA_CORTE'] = '2026-07-15'
    clientes['PAGO'] = ''
    _escribir('clientes.csv', clientes)

    _escribir('materiales.csv', pd.DataFrame(
        MATERIALES, columns=['CODIGO', 'NOMBRE', 'UNIDAD']))

    # Geo: coordenadas dentro de la Región de Coquimbo, pero inventadas.
    geo = pd.DataFrame([
        (sid, -30.60 - i * 0.01, -71.20 - i * 0.01, 6612000 + i * 1000, 285000 + i * 500, dirn, med)
        for i, (sid, _, _, _, _, dirn, med, _) in enumerate(CLIENTES)
    ], columns=['SERVICIO', 'LATITUDE', 'LONGITUDE', 'UTM NORTE (Y)', 'UTM ESTE (X)',
                'DIRECCION', 'MEDIDOR'])
    geo['CLIENTE'] = 'CLIENTE DE PRUEBA'
    geo['DIAMETRO'] = '13'
    _escribir('Geo_Catastro.csv', geo)

    _escribir('combustible.csv', pd.DataFrame([
        {'FECHA_REGISTRO': '2026-08-01 09:14', 'OPERADOR': '1001 - PEREZ JUAN',
         'PATENTE': 'KXPR-42', 'KM': '148320', 'NUM_FACTURA': 'F-9981',
         'LITROS': '45', 'MONTO_VALE': '58500', 'FOTO_FACTURA': '', 'FOTO_ODOMETRO': '',
         'FOTO_VALE': '', 'OBSERVACION': 'carga de prueba', 'LATITUD': '', 'LONGITUD': ''},
        {'FECHA_REGISTRO': '2026-08-03 16:02', 'OPERADOR': '1002 - ROJAS MARIA',
         'PATENTE': 'LMTS-71', 'KM': '92110', 'NUM_FACTURA': 'F-9994',
         'LITROS': '38', 'MONTO_VALE': '49400', 'FOTO_FACTURA': '', 'FOTO_ODOMETRO': '',
         'FOTO_VALE': '', 'OBSERVACION': '', 'LATITUD': '', 'LONGITUD': ''},
    ]))

    # Una solicitud por estado, para ver el flujo completo de caja chica.
    base = {c: '' for c in [
        'ID', 'FECHA_SOLICITUD', 'SOLICITANTE', 'CATEGORIA', 'DESCRIPCION', 'MONTO_SOLICITADO',
        'ESTADO', 'FECHA_APROBACION', 'COMENTARIO_APROBACION', 'TIPO_DOCUMENTO', 'NUM_DOCUMENTO',
        'RUT_PROVEEDOR', 'RAZON_SOCIAL', 'MONTO_NETO', 'IVA', 'MONTO_TOTAL', 'FOTO_DOCUMENTO',
        'FECHA_RENDICION', 'LATITUD', 'LONGITUD']}
    _escribir('caja_chica.csv', pd.DataFrame([
        {**base, 'ID': '1', 'FECHA_SOLICITUD': '2026-08-02 10:30',
         'SOLICITANTE': '3001 - SOTO PATRICIA', 'CATEGORIA': 'MATERIALES',
         'DESCRIPCION': 'Fittings para reparación', 'MONTO_SOLICITADO': '35000',
         'ESTADO': 'PENDIENTE'},
        {**base, 'ID': '2', 'FECHA_SOLICITUD': '2026-07-28 08:45',
         'SOLICITANTE': '3001 - SOTO PATRICIA', 'CATEGORIA': 'FLETE',
         'DESCRIPCION': 'Traslado de escombros', 'MONTO_SOLICITADO': '60000',
         'ESTADO': 'APROBADA', 'FECHA_APROBACION': '2026-07-28 11:00'},
        {**base, 'ID': '3', 'FECHA_SOLICITUD': '2026-07-20 14:10',
         'SOLICITANTE': '3001 - SOTO PATRICIA', 'CATEGORIA': 'MATERIALES',
         'DESCRIPCION': 'Cemento y arena', 'MONTO_SOLICITADO': '48000',
         'ESTADO': 'RENDIDA', 'FECHA_APROBACION': '2026-07-20 15:30',
         'TIPO_DOCUMENTO': 'BOLETA', 'NUM_DOCUMENTO': '552310',
         'RUT_PROVEEDOR': '76.111.222-3', 'RAZON_SOCIAL': 'FERRETERIA DE PRUEBA LTDA',
         'MONTO_NETO': '40336', 'IVA': '7664', 'MONTO_TOTAL': '48000',
         'FECHA_RENDICION': '2026-07-22 09:00'},
    ]))

    print("Listo. Corre la app con: python app.py")


if __name__ == '__main__':
    main()
