---
name: cargar-repo-manual
description: Carga en NyR una reposición (o una improcedencia de repo) que el operador hizo en terreno y que no quedó en la PDA, porque la orden de reposición llegó a NyR después. Úsala siempre que Danna diga "sube esta reposición", "carga la repo", "repo manual", "cortó y repuso", o pegue fotos de una reposición con un número de servicio, aunque no lo diga con esas palabras. Registra la repo en la cola de Taypi (Repos y cortes manuales) y la carga con cargar_manual.py: asigna, cierra efectiva y sube las fotos.
---

# Cargar una repo manual en NyR

Autorizado por Jorge el 2026-10-05: Danna hace esto todos los días y sabe más que tú del proceso.
**Modo trabajo:** no le expliques el proceso ni le hagas preguntas para que piense. Pide solo los
datos que falten, **todos juntos en un mensaje**, y avanza.

## Qué pasó (para ti, no para ella)

El operador corta, el cliente paga al tiro y el operador repone ahí mismo, pero la orden de
reposición llega a NyR 5 a 10 minutos después, cuando él ya se fue. Manda las fotos por WhatsApp y
alguien la carga. La cola de Taypi (`C:\SERVER\data\manuales.csv`) y el bot `cargar_manual.py`
hacen la carga completa: buscan la orden de REPOSICIÓN del servicio, la asignan al operador, la
cierran efectiva (código de orden 1, gestión = código de acción, lectura, fecha y hora) y suben
las fotos.

## 1. Juntar los datos

| Dato | De dónde | Notas |
|---|---|---|
| Servicio | su mensaje | solo números |
| Operador | su mensaje, o quien tenía el corte en la PDA (`bandeja_nyr.csv`, `ordenes_nyr_AAAAMM.csv`) | en la cola va como `NOMBRE APELLIDO` tal cual en `C:\SERVER\data\operadores.csv` (o `CODIGO - NOMBRE`) |
| Resultado | su mensaje | EFECTIVA (lo normal) o IMPROCEDENTE |
| Código de acción | ella | 1 llave de paso, 2 retiro de pieza, 3 cañería sin pavimento, 4 con pavimento, 11 llave de vereda. Improcedencia de repo: 6 casa cerrada, 21 instalación defectuosa |
| Lectura | foto del medidor | número entero. Si la foto está borrosa, dile qué lees y que lo confirme |
| Fecha y hora de ejecución | ella (la hora del WhatsApp) | WhatsApp borra la hora de las fotos. Si queda antes de la generación de la orden, el bot usa generación + 5 min |
| Fotos | las que pegue | obligatorias: fachada, instalación y medidor (en improcedencia: fachada e instalación). Opcionales: documento y número fiscal. Si no es obvio cuál es cuál, pregúntale |
| Observación | opcional | en improcedencia es obligatoria (mínimo una frase; la ve ADA) |

Lo que puedas sacar de los archivos, sácalo y muéstraselo para que lo confirme de un vistazo. Solo
pregunta lo que de verdad falta.

## 2. Registrar en la cola

1. Guarda las fotos que pegó en `danna/datos/casos/AAAA-MM-DD_repo-<servicio>/` (respaldo local).
2. Cópialas a `C:\SERVER\fotos\manuales\` con el nombre que usa Taypi:
   `MAN_<servicio>_<fachada|instalacion|medidor|documento|numero>_<AAAAMMDD>_<HHMMSS>.jpg`
   (con la fecha y hora del momento de registro).
3. Revisa que el servicio no tenga ya una fila PENDIENTE en la cola
   (`manuales.listar(estado='PENDIENTE')`), para no duplicarla.
4. Valida y registra con el mismo módulo que usa la app. No edites el CSV a mano:

python -c "import sys; sys.path.insert(0, r'C:\SERVER'); import manuales; d = {'TIPO':'REPOSICION', 'RESULTADO':'EFECTIVA', 'SERVICIO':'<servicio>', 'OPERADOR':'<NOMBRE APELLIDO>', 'CODIGO':'<codigo>', 'LECTURA':'<lectura>', 'FECHA_EJECUCION':'AAAA-MM-DD', 'HORA_EJECUCION':'HH:MM', 'OBSERVACION':'', 'FOTO_FACHADA':'<archivo>', 'FOTO_INSTALACION':'<archivo>', 'FOTO_MEDIDOR':'<archivo>', 'FOTO_DOCUMENTO':'', 'FOTO_NUMERO_FISCAL':''}; e = manuales.validar(d); print(e) if e else print('ID', manuales.registrar(d))"

$skill = @'
---
name: cargar-repo-manual
description: Carga en NyR una reposición (o una improcedencia de repo) que el operador hizo en terreno y que no quedó en la PDA, porque la orden de reposición llegó a NyR después. Úsala siempre que Danna diga "sube esta reposición", "carga la repo", "repo manual", "cortó y repuso", o pegue fotos de una reposición con un número de servicio, aunque no lo diga con esas palabras. Registra la repo en la cola de Taypi (Repos y cortes manuales) y la carga con cargar_manual.py: asigna, cierra efectiva y sube las fotos.
---

# Cargar una repo manual en NyR

Autorizado por Jorge el 2026-10-05: Danna hace esto todos los días y sabe más que tú del proceso.
**Modo trabajo:** no le expliques el proceso ni le hagas preguntas para que piense. Pide solo los
datos que falten, **todos juntos en un mensaje**, y avanza.

## Qué pasó (para ti, no para ella)

El operador corta, el cliente paga al tiro y el operador repone ahí mismo, pero la orden de
reposición llega a NyR 5 a 10 minutos después, cuando él ya se fue. Manda las fotos por WhatsApp y
alguien la carga. La cola de Taypi (`C:\SERVER\data\manuales.csv`) y el bot `cargar_manual.py`
hacen la carga completa: buscan la orden de REPOSICIÓN del servicio, la asignan al operador, la
cierran efectiva (código de orden 1, gestión = código de acción, lectura, fecha y hora) y suben
las fotos.

## 1. Juntar los datos

| Dato | De dónde | Notas |
|---|---|---|
| Servicio | su mensaje | solo números |
| Operador | su mensaje, o quien tenía el corte en la PDA (`bandeja_nyr.csv`, `ordenes_nyr_AAAAMM.csv`) | en la cola va como `NOMBRE APELLIDO` tal cual en `C:\SERVER\data\operadores.csv` (o `CODIGO - NOMBRE`) |
| Resultado | su mensaje | EFECTIVA (lo normal) o IMPROCEDENTE |
| Código de acción | ella | 1 llave de paso, 2 retiro de pieza, 3 cañería sin pavimento, 4 con pavimento, 11 llave de vereda. Improcedencia de repo: 6 casa cerrada, 21 instalación defectuosa |
| Lectura | foto del medidor | número entero. Si la foto está borrosa, dile qué lees y que lo confirme |
| Fecha y hora de ejecución | ella (la hora del WhatsApp) | WhatsApp borra la hora de las fotos. Si queda antes de la generación de la orden, el bot usa generación + 5 min |
| Fotos | las que pegue | obligatorias: fachada, instalación y medidor (en improcedencia: fachada e instalación). Opcionales: documento y número fiscal. Si no es obvio cuál es cuál, pregúntale |
| Observación | opcional | en improcedencia es obligatoria (mínimo una frase; la ve ADA) |

Lo que puedas sacar de los archivos, sácalo y muéstraselo para que lo confirme de un vistazo. Solo
pregunta lo que de verdad falta.

## 2. Registrar en la cola

1. Guarda las fotos que pegó en `danna/datos/casos/AAAA-MM-DD_repo-<servicio>/` (respaldo local).
2. Cópialas a `C:\SERVER\fotos\manuales\` con el nombre que usa Taypi:
   `MAN_<servicio>_<fachada|instalacion|medidor|documento|numero>_<AAAAMMDD>_<HHMMSS>.jpg`
   (con la fecha y hora del momento de registro).
3. Revisa que el servicio no tenga ya una fila PENDIENTE en la cola
   (`manuales.listar(estado='PENDIENTE')`), para no duplicarla.
4. Valida y registra con el mismo módulo que usa la app. No edites el CSV a mano:

       python -c "import sys; sys.path.insert(0, r'C:\SERVER'); import manuales; d = {'TIPO':'REPOSICION', 'RESULTADO':'EFECTIVA', 'SERVICIO':'<servicio>', 'OPERADOR':'<NOMBRE APELLIDO>', 'CODIGO':'<codigo>', 'LECTURA':'<lectura>', 'FECHA_EJECUCION':'AAAA-MM-DD', 'HORA_EJECUCION':'HH:MM', 'OBSERVACION':'', 'FOTO_FACHADA':'<archivo>', 'FOTO_INSTALACION':'<archivo>', 'FOTO_MEDIDOR':'<archivo>', 'FOTO_DOCUMENTO':'', 'FOTO_NUMERO_FISCAL':''}; e = manuales.validar(d); print(e) if e else print('ID', manuales.registrar(d))"

   Si `validar` devuelve errores, corrígelos con ella antes de registrar.

## 3. Ensayo, confirmación y carga

En `C:\BD\Drive\TI\Urjta-Cobranza\scrapers`:

1. `python cargar_manual.py --ensayo --id <ID>` dice qué haría (orden, operador, código, fecha,
   fotos) sin tocar NyR ni la cola. Muéstraselo en una tabla corta.
2. Con su **sí**, corre `python cargar_manual.py --id <ID>`. Si tu clasificador bloquea la escritura
   en NyR, no busques otro camino: pásale ese comando en un bloque para que lo corra ella. Si no hay
   apuro, también puede quedar en la cola: la tarea "URJTA Cola Manuales" la carga sola.
3. Comprueba el resultado: `manuales.obtener('<ID>')` tiene que quedar CARGADA con su número de
   orden (o con el motivo, si no se pudo). Dile en una línea cómo quedó.

El bot resuelve solo dos casos que conviene contarle: si la orden ya estaba DESCARGADO PDA (alguien
la cargó), no la toca y marca la fila con quién la ejecutó; si la orden todavía no aparece en NyR,
la fila queda PENDIENTE y se carga en la corrida siguiente.

## 4. Registro

Una línea en `danna/CASOS.md` **solo si el caso tuvo algo raro** (algo que falló, un dato que no
calzaba, algo nuevo). Lo de todos los días ya queda en `cierres_log\cierres_http.csv` y en la cola.