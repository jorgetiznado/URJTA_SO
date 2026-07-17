"""
sync_pipeline.py
=================
Ingesta desde el pipeline real de Urjta-Cobranza (C:\\BD\\SGC\\Salidas\\seguimiento.parquet)
hacia el formato clientes.csv que usa la app de campo.

Reemplaza la carga manual de CSV en Admin: en vez de que alguien suba un archivo a mano,
esto lee directo la salida ya validada del pipeline canónico (seguimiento_nyr.py).

Filtro de "pendientes" confirmado contra medidas.py::ordenes_pendientes():
    TIPO_RESULTADO == 'PENDIENTE' AND TIPO_ACCION == 'CORTE', sobre PERIODO_ORDEN.

Nota sobre operador: el pendiente trae RESPONSABLE (asignado en NyR/Qlik antes de
llegar a terreno), no OPERADOR (que solo se llena al ejecutar el PDA). Los pendientes
sin RESPONSABLE asignado son responsabilidad de back office (Danna Peralta / Rodrigo
Bravo) — quedan en la lista con OPERADOR vacío, visibles solo para roles que ven todo.
"""

import pandas as pd

PARQUET_PATH = r"C:\BD\SGC\Salidas\seguimiento.parquet"
EEPP_PATH    = r"C:\BD\SGC\Salidas\eepp_final.csv"

COLUMNAS_CLIENTES = [
    'ID_SERVICIO', 'FECHA_CORTE', 'DEUDA', 'ANTIGUEDAD',
    'TIPO CORTE', 'OPERADOR', 'DIRECCION', 'MEDIDOR', 'LOCALIDAD', 'PAGO',
]


def periodo_mas_reciente():
    """Último PERIODO_ORDEN presente en el pipeline (para default del sync)."""
    df = pd.read_parquet(PARQUET_PATH, columns=['PERIODO_ORDEN'])
    return int(df['PERIODO_ORDEN'].dropna().max())


def obtener_pendientes(periodo='actual'):
    """Lee seguimiento.parquet y devuelve un DataFrame con el esquema de clientes.csv.

    periodo: int tipo 202607 para filtrar por PERIODO_ORDEN (mes de generación);
             'actual' (default) usa el período más reciente disponible;
             None trae TODO el backlog pendiente histórico (miles de filas).
    """
    df = pd.read_parquet(PARQUET_PATH)

    if periodo == 'actual':
        periodo = int(df['PERIODO_ORDEN'].dropna().max())

    mask = (df['TIPO_RESULTADO'] == 'PENDIENTE') & (df['TIPO_ACCION'] == 'CORTE')
    if periodo is not None:
        mask &= (df['PERIODO_ORDEN'] == periodo)
    pend = df.loc[mask].copy()

    salida = pd.DataFrame({
        'ID_SERVICIO': pend['ID_SERVICIO'],
        'FECHA_CORTE': pd.to_datetime(pend['FECHA_GENERACION'], errors='coerce').dt.strftime('%d/%m/%Y'),
        'DEUDA':       pend['DEUDA'],
        'ANTIGUEDAD':  pend['ANTIGUEDAD'],
        'TIPO CORTE':  pend['TIPO_CORTE'],
        'OPERADOR':    pend['RESPONSABLE'],
        'DIRECCION':   pend['DIRECCION'],
        'MEDIDOR':     pend['MEDIDOR'],
        'LOCALIDAD':   pend['LOCALIDAD_C'],
        'PAGO':        pend['PAGO_FLAG'].fillna(0).astype(int),
    })

    # Un mismo servicio puede tener más de una orden pendiente entre distintos
    # períodos; nos quedamos con la más reciente por FECHA_CORTE (generación).
    salida = salida.sort_values('FECHA_CORTE').drop_duplicates('ID_SERVICIO', keep='last')

    return salida.reset_index(drop=True)


def obtener_eepp_por_periodo():
    """Ingresos (EEPP) de URJTA por PERIODO de ejecución, uniendo eepp_final.csv
    (VALOR_EEPP por NUMERO ORDEN) con seguimiento.parquet (fecha de ejecución).
    Devuelve un DataFrame: PERIODO, INGRESO_EEPP."""
    eepp = pd.read_csv(EEPP_PATH, dtype=str, sep=None, engine='python', encoding='utf-8-sig')
    seg = pd.read_parquet(PARQUET_PATH, columns=['NUMERO ORDEN', 'PERIODO'])
    m = eepp.merge(seg.drop_duplicates('NUMERO ORDEN'), on='NUMERO ORDEN', how='left')
    m['VALOR_EEPP'] = pd.to_numeric(m['VALOR_EEPP'], errors='coerce').fillna(0)
    out = m.groupby('PERIODO', dropna=True)['VALOR_EEPP'].sum().reset_index()
    out.columns = ['PERIODO', 'INGRESO_EEPP']
    out['PERIODO'] = out['PERIODO'].astype(int)
    return out.sort_values('PERIODO').reset_index(drop=True)


def obtener_resumen_operativo_por_periodo():
    """Cortes, Repos, Visitas, Improcedencias por PERIODO (fecha de ejecución) —
    misma lógica que pipeline/medidas.py (cortes/repos/visitas/improcedencia),
    vectorizado sobre todo el histórico de una sola pasada."""
    df = pd.read_parquet(
        PARQUET_PATH,
        columns=['NUMERO ORDEN', 'TIPO_ACCION', 'TIPO_RESULTADO', 'RESULTADO', 'PERIODO'],
    )
    df['PERIODO'] = df['PERIODO'].astype('Int64')
    es_corte_accion = df['TIPO_ACCION'] == 'CORTE'

    masks = {
        'CORTES':         es_corte_accion & (df['TIPO_RESULTADO'] == 'CORTE'),
        'REPOS':          (df['TIPO_ACCION'] == 'REPO') & (df['TIPO_RESULTADO'] == 'CORTE'),
        'VISITAS':        es_corte_accion & df['RESULTADO'].fillna('').str.startswith('VISITA'),
        'IMPROCEDENCIAS': es_corte_accion & (df['TIPO_RESULTADO'] == 'CORTE_IMPROCEDENTE'),
    }
    columnas = {
        nombre: df.loc[mask].groupby('PERIODO')['NUMERO ORDEN'].nunique()
        for nombre, mask in masks.items()
    }
    out = pd.DataFrame(columnas).fillna(0).astype(int).reset_index()
    out['PERIODO'] = out['PERIODO'].astype(int)
    return out.sort_values('PERIODO').reset_index(drop=True)


def obtener_resumen_unificado(meses=6):
    """La 'gran unión': Cortes/Repos/Visitas/Improcedencias + Ingreso EEPP,
    por período, últimos `meses`. Los costos (Caja Chica/Combustible, que viven
    en esta app, no en el pipeline) se agregan después en app.py."""
    op = obtener_resumen_operativo_por_periodo()
    eepp = obtener_eepp_por_periodo()
    out = op.merge(eepp, on='PERIODO', how='outer').fillna(0).sort_values('PERIODO')
    for col in ['CORTES', 'REPOS', 'VISITAS', 'IMPROCEDENCIAS']:
        out[col] = out[col].astype(int)
    return out.tail(meses).reset_index(drop=True)


if __name__ == '__main__':
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    df = obtener_pendientes(periodo=202607)
    print(f"Pendientes período 202607: {len(df)} filas")
    print(f"Con OPERADOR asignado (RESPONSABLE): {df['OPERADOR'].notna().sum()}")
    print(f"Sin asignar (back office): {df['OPERADOR'].isna().sum()}")
    print()
    print(df.head(10).to_string())
