// ============================================================
// DANNA: ESTE ARCHIVO ES TU CONTENIDO.
// Todo el texto del tablero sale de aquí (los "datos"). El diseño está en
// estilo.css y el código que lo dibuja en index.html (la "presentación").
// Separar datos de presentación es una idea clave en software: puedes
// cambiar el contenido sin tocar el diseño, y al revés.
//
// Este contenido se ve en dos lugares:
//   - en este PC: doble clic en index.html
//   - en internet: proyecto.urjta.cl/danna (lo lee en vivo; basta recargar)
//
// Va en formato JSON, que es estricto:
//   - los nombres y los textos van entre comillas dobles: "palabra": "ADA"
//   - nada de coma después del último elemento de una lista o de un { }
//   - true / false sin comillas
// Si algo queda mal escrito, la página de internet te dice en qué línea.
// Las cifras del contrato (EE.PP. por período) no van aquí: las calcula el
// sistema de URJTA y salen en la versión de internet.
// ============================================================
window.TABLERO = {
  "dueña": "Danna",
  "version": "v1",
  "actualizado": "2026-10-05",
  "intro": "Mi espacio para entender el contrato de cobranza de URJTA y aprender a construir con IA. Lo armó Jorge como punto de partida; desde aquí lo hago mío.",

  "flujo": {
    "pasos": [
      { "titulo": "Pendiente", "detalle": "ADA informa clientes con deuda. Llegan como órdenes de corte." },
      { "titulo": "Asignación", "detalle": "Cada orden queda con un RESPONSABLE antes de salir a terreno." },
      { "titulo": "Visita", "detalle": "El operador va al domicilio y registra con foto y GPS." },
      { "titulo": "Resultado", "detalle": "Corte ejecutado, o improcedencia si no se pudo (casa cerrada, arranque no ubicado…)." },
      { "titulo": "Pago y reposición", "detalle": "Si el cliente paga, se repone el servicio." },
      { "titulo": "EEPP", "detalle": "A fin de mes, las órdenes ejecutadas se cobran a ADA." }
    ],
    "aviso": "Este flujo lo escribió Claude leyendo la documentación del sistema. Puede tener errores. Tu primera tarea es revisarlo con Jorge y corregirlo: así se trabaja con IA."
  },

  "glosarioContrato": [
    { "palabra": "ADA", "significado": "Aguas del Altiplano. El cliente de URJTA: la empresa sanitaria que encarga la cobranza.", "entendida": false },
    { "palabra": "CyR", "significado": "Corte y Reposición. La línea más grande del contrato.", "entendida": false },
    { "palabra": "EEPP", "significado": "Estado de Pago. Lo que URJTA le cobra a ADA cada mes por las órdenes ejecutadas. Es el ingreso.", "entendida": false },
    { "palabra": "EERR", "significado": "Estado de Resultados. Ingresos menos costos. Dice si el contrato gana o pierde plata.", "entendida": false },
    { "palabra": "Improcedencia", "significado": "Una orden que no se pudo ejecutar, con un motivo registrado.", "entendida": false },
    { "palabra": "Período", "significado": "El mes del contrato, escrito como AAAAMM. Por ejemplo 202607 es julio de 2026.", "entendida": false },
    { "palabra": "Mismo tramo", "significado": "Comparar un mes que va en curso con los mismos días del mes anterior (del 1 al mismo día), no con el mes completo.", "entendida": false },
    { "palabra": "Caja chica", "significado": "Dinero para gastos menores de la operación. Se solicita, se aprueba y se rinde con boleta.", "entendida": false }
  ],

  "glosarioIA": [
    { "palabra": "Prompt", "significado": "Lo que le escribes a la IA. Mientras más claro el pedido, mejor el resultado.", "entendida": false },
    { "palabra": "Contexto", "significado": "Todo lo que la IA tiene a la vista en una conversación: tus mensajes, archivos que leyó, instrucciones.", "entendida": false },
    { "palabra": "Alucinación", "significado": "Cuando la IA inventa algo con total seguridad. Por eso siempre se verifica contra la fuente.", "entendida": false },
    { "palabra": "Commit", "significado": "Una foto guardada del proyecto, con un mensaje que dice qué cambió. Permite volver atrás.", "entendida": false },
    { "palabra": "Revert", "significado": "Deshacer un cambio agregando un paso nuevo que lo revierte. La historia no se borra.", "entendida": false },
    { "palabra": "CLAUDE.md", "significado": "Un archivo con instrucciones que Claude lee antes de trabajar. Es como el reglamento del proyecto.", "entendida": false },
    { "palabra": "JSON", "significado": "Un formato para escribir datos que las máquinas leen sin dudas: nombres entre comillas, listas entre [ ] y objetos entre { }.", "entendida": false }
  ],

  "construido": [
    { "fecha": "2026-10-05", "que": "El tablero pone el foco en las órdenes: lo abierto hoy en NyR de mi zona, lo más urgente, quién tiene qué, las órdenes con muchos intentos (repitencias) y un buscador con el historial completo de cada servicio.", "quien": "Jorge con Claude" },
    { "fecha": "2026-10-05", "que": "El tablero sale a internet (proyecto.urjta.cl/danna) con el EE.PP. por período y por zona, mes a mes en vez de acumulado. El contenido pasa a contenido.js y el diseño a estilo.css.", "quien": "Jorge con Claude" },
    { "fecha": "2026-10-05", "que": "Nace el tablero (versión 0): cifras del contrato, flujo de una orden, glosarios y bitácora.", "quien": "Jorge con Claude" }
  ],

  "mision": {
    "titulo": "Revisar el flujo y hacer tu primer cambio",
    "pasos": [
      "Abre tu tablero en internet y elige distintos meses: ¿qué mes fue el más alto y por qué crees que fue?",
      "Lee el flujo de una orden y anota qué no entiendes.",
      "Pregúntale a Jorge si los pasos están bien y corrige lo que esté mal.",
      "Pídele a Claude: <code>cambia el flujo con estas correcciones</code> y mira cómo lo hace.",
      "Al terminar, pídele a Claude que cierre la sesión en la bitácora."
    ]
  }
};
