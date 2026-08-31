# Nómina de Asistencia por QR

**Módulo:** Asistencia · **Estado:** listo para piloto · **Datos:** `asistencia.csv`,
`asistencia_justificaciones.csv`

Reemplaza el libro de asistencia en papel del punto de reunión. El trabajador marca
escaneando un QR que rota en la pantalla del supervisor; la nómina del día se arma sola.

---

## 1. Cómo se usa en terreno

### El día a día

1. **El supervisor** abre `/asistencia/qr` en un teléfono, tablet o notebook en el punto de
   reunión, y elige el punto (`BASE URJTA`, un frente de trabajo, etc.).
2. **Cada trabajador** escanea el QR con la cámara de su teléfono. Se abre la app, confirma
   quién es y toca **Registrar entrada**. Listo — dos segundos por persona.
3. Al terminar la jornada se repite: el sistema sabe que ahora corresponde **SALIDA**.
4. **Administración** entra a `/admin/asistencia` y ve la nómina del día: quién llegó, a qué
   hora, cuántas horas lleva y quién no ha marcado.

### Quien no anda con smartphone

Se imprimen las **credenciales** desde `/asistencia/credenciales` (una tarjeta con QR por
trabajador). El supervisor abre `/asistencia/escanear` en su propio teléfono y les pasa la
credencial por la cámara. Queda registrado el marcaje y quién lo hizo.

Si tampoco hay credencial, el supervisor puede registrar el marcaje **a mano** — exige
escribir el motivo y queda marcado como `MANUAL` con su nombre.

---

## 2. Por qué no se puede marcar desde la casa

El QR de jornada **no es fijo**: contiene un token firmado con `URJTA_SECRET_KEY` que incluye
la ventana de 30 segundos en que fue emitido.

| Intento | Qué pasa |
|---|---|
| Le saco una foto al QR y la mando por WhatsApp | El token vence a los ~90 s: llega muerto |
| Me guardo el link de ayer | Vencido |
| Me invento un token | La firma no cuadra — rechazado |
| Cambio la hora de mi teléfono | La hora la pone el servidor, no el teléfono |
| Me imprimo una credencial con el código de otro | Va firmada: sin la clave del servidor no se puede fabricar |

Además, cada marcaje guarda el GPS del teléfono (si el trabajador acepta el permiso), el punto
de reunión y el origen (`QR_JORNADA`, `CREDENCIAL` o `MANUAL`). La pantalla de Admin enlaza
cada marcaje a Google Maps.

**Lo que este diseño no cubre:** un trabajador puede prestarle su teléfono ya logueado a otro
que esté en el punto de reunión. Contra eso sirve que el supervisor esté ahí mirando —
es el mismo control que existía con el libro en papel.

---

## 3. Permisos

| Quién | Puede |
|---|---|
| Cualquier usuario con sesión | Marcar su entrada/salida, ver su propia asistencia y su mes |
| ADMINISTRATIVO / SUPERVISOR | + Mostrar el QR de jornada, escanear credenciales, ver e intervenir la nómina |
| ADMINISTRADOR DE CONTRATO | Lo mismo |
| DIRECCION / GERENCIA | Lo mismo |
| Clave maestra de Admin | Lo mismo (vía `/admin`) |

Un operador que entre a `/asistencia/qr` o `/admin/asistencia` recibe **403**.

---

## 4. Estados de la nómina

| Estado | Cuándo |
|---|---|
| `PRESENTE` | Marcó dentro del horario (entrada + tolerancia) |
| `ATRASO` | Marcó después de la tolerancia — la nómina muestra los minutos |
| `AUSENTE` | Día hábil, no marcó y no tiene justificación |
| `JUSTIFICADO` | Tiene licencia, vacaciones o permiso cargado para esa fecha |
| `NO LABORAL` | El día no está en los días hábiles configurados (por defecto, domingo), **o es un día hábil en que no marcó nadie** (feriado, día sin faena, o el sistema todavía no estaba en uso) |

Un día hábil en que *nadie* marcó no le cuenta falta a toda la dotación — sería un feriado o
un día sin faena, y ensuciaría el cierre de mes. La excepción es **hoy**: la nómina del día en
curso sí muestra quién no ha marcado, que es justamente para lo que se mira.

Las **horas trabajadas** suman los tramos ENTRADA→SALIDA, así que la colación se descuenta
sola si se marca. Una ENTRADA sin su SALIDA queda como *jornada abierta* y no suma horas
hasta que se cierre (Admin puede cerrarla con un marcaje manual).

---

## 5. Configuración (`.env`)

| Variable | Por defecto | Qué hace |
|---|---|---|
| `URJTA_ASISTENCIA_HORA_ENTRADA` | `08:30` | Hora de inicio de jornada, para calcular atrasos |
| `URJTA_ASISTENCIA_TOLERANCIA_MIN` | `10` | Minutos de gracia antes de contar atraso |
| `URJTA_ASISTENCIA_PUNTOS` | `BASE URJTA` | Puntos de reunión, separados por coma |
| `URJTA_ASISTENCIA_DIAS_HABILES` | `1,2,3,4,5,6` | Días laborales (1=lunes … 7=domingo) |

La firma de los QR usa `URJTA_SECRET_KEY`, la misma clave de sesión de la app.
**Si se cambia esa clave hay que reimprimir las credenciales** (las viejas dejan de validar).

---

## 6. Archivos de datos

`data/asistencia.csv` — un marcaje por fila (`;` como separador):

```
ID;FECHA;HORA;TIPO;CODIGO;NOMBRE;CARGO;ORIGEN;PUNTO;LATITUD;LONGITUD;REGISTRADO_POR;OBSERVACION
```

`data/asistencia_justificaciones.csv`:

```
FECHA;CODIGO;NOMBRE;MOTIVO;COMENTARIO;REGISTRADO_POR;FECHA_REGISTRO
```

Los marcajes se **agregan al final** del archivo, nunca se reescribe completo: en el punto de
reunión marcan varias personas al mismo tiempo, y un ciclo leer-modificar-escribir perdería
marcajes.

La **nómina no se guarda**: se calcula a partir de los marcajes, de `operadores.csv` (dotación
activa) y de las justificaciones. Así nunca queda desincronizada — si se corrige un marcaje,
la nómina se corrige sola.

### Descargas

- `/descargar/asistencia` — marcajes en crudo, para auditoría.
- `/descargar/nomina-asistencia?desde=01/09/2026&hasta=30/09/2026` — la nómina consolidada,
  una fila por trabajador y día, con horas y estado. **Este es el archivo para cerrar el mes.**
  Sin parámetros, entrega del día 1 del mes hasta hoy.

---

## 7. Rutas

| Ruta | Quién | Qué hace |
|---|---|---|
| `/asistencia` | Con sesión | Mi estado de hoy, mis marcajes, mi mes |
| `/asistencia/marcar?t=<token>` | Con sesión | Pantalla que abre el QR — confirma y registra |
| `/asistencia/qr` | Gestión | Pantalla del QR rotativo del punto de reunión |
| `/asistencia/qr.svg` | Gestión | Imagen del QR vigente (la pantalla la renueva sola) |
| `/asistencia/qr/estado` | Gestión | JSON con el avance en vivo (presentes, últimos marcajes) |
| `/asistencia/escanear` | Gestión | Escáner de credenciales + registro manual |
| `/asistencia/credenciales` | Gestión | Hoja imprimible de credenciales |
| `/admin/asistencia` | Gestión | La nómina del día + acumulado del mes |

---

## 8. Dependencia nueva

Generar los QR necesita **[segno](https://pypi.org/project/segno/)** (Python puro, sin
compilar nada):

```
pip install segno
```

Si falta, el resto del módulo funciona igual — solo las dos pantallas con QR avisan que hay
que instalarla. La lectura de credenciales en el teléfono del supervisor usa el lector de QR
del propio navegador (`BarcodeDetector`, disponible en Chrome/Android); si el navegador no lo
soporta, la pantalla ofrece el registro manual.

---

## 9. Pruebas

```
python test_asistencia.py
```

Cubre la firma y el vencimiento de los tokens, las credenciales falsificadas, la alternancia
entrada/salida, el doble escaneo, el cálculo de horas con colación y la clasificación de
estados de la nómina.

---

## 10. Pendientes conocidos

- **La sesión se cae y hay que reloguearse.** Si el trabajador no tiene sesión activa cuando
  escanea, alcanza a vencerse el token mientras entra su PIN y tiene que escanear de nuevo.
  Se resuelve dejando la sesión persistente (cookie de larga duración) — decisión de seguridad
  a tomar con Jorge.
- **Sin geocerca.** Se guarda el GPS pero no se rechaza un marcaje lejano. Se puede agregar
  cuando estén las coordenadas de cada punto de reunión.
- **Migración a SQLite** junto con el resto de los módulos (ver `PLAN_FORMALIZACION.md`).
