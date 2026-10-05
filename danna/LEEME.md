# Hola, Danna

Este es tu espacio. Aquí vas a aprender cómo funciona el contrato de cobranza de URJTA y, al mismo
tiempo, cómo se construye con inteligencia artificial. Tu tablero (`tablero/index.html`) es tuyo:
puedes cambiarlo, agrandarlo y llevarlo donde quieras.

Tres cosas para estar tranquila:

- **Todo queda registrado.** Cada cambio se guarda en la historia del proyecto y en `BITACORA.md`.
- **Todo se puede deshacer.** Si algo no te gusta o se rompe, se vuelve atrás.
- **No puedes romper el sistema real.** Claude tiene instrucciones de solo leer los datos y NyR,
  y de escribir únicamente dentro de esta carpeta.

---

## Cómo empezar una sesión (en el PC)

1. Abre una terminal (PowerShell).
2. Entra a tu carpeta:
   ```
   cd C:\ruta\a\URJTA_SO\danna
   ```
   (Jorge te dice la ruta exacta la primera vez.)
3. Escribe `claude` y presiona Enter.
4. Primer mensaje:
   > Hola, soy Danna. Lee la bitácora y cuéntame dónde quedamos.
5. Para ver tu tablero: doble clic en `tablero\index.html`. Cuando Claude haga un cambio, recarga
   la página (F5).

## Frases útiles

| Quieres… | Dile a Claude |
|---|---|
| Entender algo | "¿Qué significa EEPP?" / "Explícame qué acabas de hacer" |
| Cambiar el tablero | "Agrega una sección con…" / "Cambia el color de…" |
| Ir con cuidado | "Antes de esto, guardemos un punto" |
| Deshacer | "Deshaz lo último" / "Muéstrame los cambios de hoy, quiero volver atrás" |
| Ver tu historia | "Muéstrame qué he construido hasta ahora" |
| Terminar | "Cerremos la sesión" (anota todo en la bitácora y lo respalda) |

## Una regla de oro

La IA se equivoca, a veces con mucha seguridad. Cuando te dé un número o una explicación del
contrato, pregúntale **de dónde lo sacó**. Si no tiene fuente, verifícalo con Jorge. Aprender a
dudar bien es la mitad de saber usar IA.

---

## Para Jorge — preparación (una sola vez)

1. En el PC donde trabajará Danna (idealmente **no** el servidor de producción), con el repo ya
   clonado: `git pull` en `main` para traer esta carpeta.
2. Crear su rama: `git checkout -b danna main` y `git push -u origin danna`.
3. Verificar que Claude Code abre desde `URJTA_SO\danna` y lee `danna/CLAUDE.md`.
4. Recomendado: modo de permisos por defecto (Claude pide permiso antes de editar o ejecutar), así
   Danna ve y aprueba cada acción. Es parte del aprendizaje.
5. Pendiente: agregar reglas de permisos que bloqueen escritura en `C:\BD` y `C:\SERVER` (pedírselo
   a Claude en la primera sesión local con `/permissions`).
