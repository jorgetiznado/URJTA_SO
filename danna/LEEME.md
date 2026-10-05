# Hola, Danna

Este es tu espacio. Aquí vas a aprender cómo funciona el contrato de cobranza de URJTA y, al mismo
tiempo, cómo se construye con inteligencia artificial. Tu tablero es tuyo: puedes cambiarlo,
agrandarlo y llevarlo donde quieras.

Y en NyR la experta eres tú: Claude va a aprender de ti.

Tres cosas para estar tranquila:

- **Todo queda registrado.** Cada cambio se guarda en la historia del proyecto y en `BITACORA.md`.
- **Todo se puede deshacer.** Si algo no te gusta o se rompe, se vuelve atrás.
- **Lo real se mira, no se toca.** Claude lee los datos y NyR, pero solo escribe en esta carpeta.
  La única excepción es corregir una orden mal ingresada en NyR. En ese caso, Claude te muestra
  antes qué va a cambiar, y el guardado lo haces tú.

---

## Cómo empezar una sesión

1. Abre la app de Claude, pestaña **Code**, y empieza una sesión nueva en la carpeta
   `C:\Danna\URJTA_SO\danna`.
2. Primer mensaje:
   - **La primera vez:** "Hola, soy Danna, esta es mi primera vez."
   - **Las siguientes:** "Hola, soy Danna. Lee la bitácora y cuéntame dónde quedamos."
3. Para ver tu tablero:
   - **Desde cualquier lado:** entra a **proyecto.urjta.cl/danna** con tu usuario de URJTA. Ahí están
     las cifras del contrato mes a mes, con filtros por período y por zona, y tus dashboards.
   - **En este PC:** doble clic en `tablero\index.html`.
   Cuando Claude haga un cambio, recarga la página (F5): las dos versiones leen los mismos archivos.

La sesión está abierta con la cuenta de Jorge, así que vas a ver su nombre en algunas partes. Es
normal: Claude sabe que en esta carpeta eres tú.

## Frases útiles

| Quieres… | Dile a Claude |
|---|---|
| Entender algo | "¿Qué significa EEPP?" / "Explícame qué acabas de hacer" |
| Cambiar el tablero | "Agrega una sección con…" / "Cambia el color de…" |
| Un dashboard | "Quiero saber… armemos un dashboard" |
| Ver algo de NyR | "¿Qué tiene abierto hoy el operador…?" / "Mira esta orden" |
| Traer un caso | Pega la captura o el WhatsApp: "Revisemos este caso" |
| Enseñarle a Claude | "Te explico cómo funciona…" / "Esto siempre se hace así" |
| Crear una habilidad | "Convirtamos esto en una habilidad" |
| Ir con cuidado | "Antes de esto, guardemos un punto" |
| Deshacer | "Deshaz lo último" / "Muéstrame los cambios de hoy, quiero volver atrás" |
| Ver tu historia | "Muéstrame qué he construido hasta ahora" |
| Terminar | "Cerremos la sesión" (anota todo en la bitácora y lo respalda) |

## Tus archivos

- `BITACORA.md`: el diario de cada sesión.
- `NYR.md`: cómo Claude mira NyR y **lo que tú le enseñas**.
- `CASOS.md`: los casos que revisan juntas y lo que dejó cada uno.
- `.claude/skills/`: tus habilidades (instrucciones que Claude aprende de ti y repite siempre bien).
- `tablero/`: tu tablero y tus dashboards.
- `datos/`: copias con datos de clientes. Nunca se suben a internet.

## Una regla de oro

La IA se equivoca, a veces con mucha seguridad. Cuando te dé un número o una explicación del
contrato, pregúntale **de dónde lo sacó**. Si no tiene fuente, verifícalo con Jorge. Y si te dice
algo de NyR que tú sabes que no es así, díselo: también aprende de ti.
