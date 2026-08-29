# Metodología de construcción

## Propósito

Este directorio es la memoria operativa del proyecto de monitorización. Aquí el
diseñador divide el trabajo en tareas pequeñas y cualquier agente puede conocer
el estado real, ejecutar una tarea o continuarla sin depender del historial de
una conversación.

Los documentos deben ser breves, concretos y suficientes para trabajar. No se
copiarán logs extensos ni explicaciones generales que ya estén en
[`../README.md`](../README.md).

## Fuentes de verdad

1. `../README.md` define el producto y su arquitectura.
2. El fichero individual de una tarea define su alcance y estado real.
3. [`TASKS.md`](TASKS.md) es el índice resumido de todas las tareas.
4. [`HERMES_TASK_GUIDE.md`](HERMES_TASK_GUIDE.md) define el contrato de
   ejecución del agente local.

Si el índice y una tarea discrepan, manda el fichero individual. El siguiente
agente corregirá el índice antes de continuar.

## Estructura

```text
building/
├── README.md
├── HERMES_TASK_GUIDE.md
├── TASKS.md
├── TASK_TEMPLATE.md
├── audits/
│   └── TASK-NNN-agente.md
└── tasks/
    ├── TASK-001-titulo-breve.md
    └── TASK-002-titulo-breve.md
```

Los identificadores son consecutivos, no se reutilizan y forman parte del
nombre del fichero. El título empieza con un verbo y describe un único
resultado, por ejemplo `TASK-003-configurar-prometheus.md`.

## Roles

### Diseñador

El diseñador mantiene la visión técnica y prepara el trabajo. Debe:

- inspeccionar el estado actual antes de crear tareas;
- dividir los cambios en unidades pequeñas e independientes;
- declarar dependencias, límites y riesgos;
- definir criterios de aceptación observables;
- indicar cómo verificar el resultado;
- mantener `TASKS.md` ordenado y coherente;
- actualizar la arquitectura cuando una decisión de tarea la modifique.

Una tarea no se marca como `ready` si obliga al ejecutor a decidir una parte
esencial del producto. Primero debe resolverse o documentarse esa decisión.

### Ejecutor

El ejecutor puede ser cualquier agente. Debe:

- leer este documento, el índice, la tarea y sus dependencias;
- reclamar la tarea antes de modificar código;
- respetar el alcance y no ampliar el trabajo silenciosamente;
- verificar en proporción al riesgo;
- actualizar el documento con resultados y estado final;
- dejar un traspaso claro si no puede terminar.

El ejecutor puede tomar decisiones locales y reversibles. Una decisión que
cambie arquitectura, seguridad, datos persistidos o interfaces públicas debe
volver al diseñador o quedar bloqueada para revisión.

### Orquestador

El orquestador prepara la ejecución y no delega control de proceso al modelo.
En tareas con `Execution: orchestrated` debe:

- validar dependencias y preflight;
- ejecutar el preflight literal de la tarea sobre el baseline limpio antes de
  reclamarla;
- crear el worktree y fijar la raíz autorizada;
- reclamar y actualizar la tarea antes de invocar Hermes;
- limitar perfil, herramientas, turnos, salida y tiempo;
- conservar candidato y telemetría;
- auditar todas las salidas, incluso sin `PASS`;
- acumular el resultado de todas las verificaciones, sin aceptar por el código
  del último comando;
- repetir un resumen de fallos al final del log y usarlo como devolución
  concreta durante un máximo de tres rondas;
- conservar en el job y retirar del worktree cualquier artefacto fuera de
  alcance antes del siguiente intento;
- trasladar a `review` sólo una entrega con todos los comandos en verde;
- encargar la aceptación a un auditor independiente.

Hermes no modifica los documentos de workflow de `building/` en este modo. Su
autonomía se limita a los archivos técnicos declarados y a ejecutar sus
verificaciones.

## Tamaño de una tarea

Cada tarea debe cumplir estas reglas:

- persigue un solo resultado verificable;
- puede completarse normalmente en una sesión de trabajo;
- afecta a un conjunto reducido y explícito de archivos;
- tiene entre uno y cinco pasos principales;
- termina con una comprobación reproducible;
- no mezcla investigación, implementación y despliegue si pueden separarse.

Si la descripción necesita varias entregas independientes, el diseñador la
divide en tareas y declara las dependencias entre ellas.

Para Hermes se aplican además los límites de
[`HERMES_TASK_GUIDE.md`](HERMES_TASK_GUIDE.md): máximo dos archivos técnicos y
uno de pruebas, entre cuatro y seis comportamientos verificables y una sola
interfaz principal. Si no cabe previsiblemente en una ronda de 12 iteraciones,
se divide antes de marcar `ready`. Las rondas adicionales corrigen defectos; no
justifican una tarea inicial mayor.

## Estados

| Estado | Significado |
|---|---|
| `draft` | Falta una decisión, información o definición del diseñador |
| `ready` | Está completamente definida; se reclama cuando sus dependencias estén `done` |
| `in_progress` | Un agente la ha reclamado y está trabajando en ella |
| `blocked` | No puede continuar sin una decisión o cambio externo concreto |
| `review` | El ejecutor terminó y espera verificación independiente |
| `done` | El auditor verificó y aceptó el resultado |
| `cancelled` | Ya no debe ejecutarse; el motivo queda documentado |

Transiciones normales:

```text
draft --> ready --> in_progress --> review --> done
             ^               |           |
             +---- blocked <--+           +--> ready
```

No se usa un estado ambiguo como `almost_done`. El trabajo pendiente se
describe con casillas sin marcar y el estado permanece `in_progress`.

## Cómo crea una tarea el diseñador

1. Lee `TASKS.md` y elige el siguiente identificador disponible.
2. Copia `TASK_TEMPLATE.md` a `tasks/TASK-NNN-titulo.md`.
3. Completa objetivo, alcance, dependencias, pasos y aceptación.
4. Elimina apartados que no aporten información; no deja marcadores genéricos.
5. Marca `ready` sólo si otro agente puede empezar sin preguntar qué construir.
6. Añade o actualiza la fila correspondiente en `TASKS.md`.

Antes de marcar `ready`, el diseñador ejecuta el preflight en el mismo tipo de
entorno que usará el agente. No publica comandos que dependan de herramientas
ausentes. Cada criterio debe indicar directorio, comando y código esperado.

El diseñador aporta tests de contrato que Hermes no puede modificar. Si cubren
todos los comportamientos, Hermes no crea un segundo archivo de tests. Sólo se
permiten tests propios para un caso relevante ausente del contrato.
Para formatos de texto incluye al menos un ejemplo válido y uno inválido.

El diseñador enlaza rutas y documentos, pero no duplica su contenido. Los
comandos de verificación deben ser seguros y ejecutables desde la raíz del
repositorio, salvo que se indique otra ubicación.

## Cómo reclama y ejecuta una tarea un agente

1. Confirma que está `ready` y que todas sus dependencias están `done`.
2. Vuelve a leer el fichero justo antes de reclamarlo.
3. Cambia el estado a `in_progress`, añade su identificador en `Owner` y la
   hora UTC en `Updated`.
4. Actualiza también la fila de `TASKS.md`.
5. Implementa únicamente el alcance acordado.
6. Marca cada paso terminado y registra las verificaciones realizadas.
7. Si considera satisfechos los criterios, cambia el estado a `review` y
   limpia `Owner`; sólo el auditor puede marcar `done`.
8. Actualiza `TASKS.md` en el mismo cambio.

En `Execution: orchestrated`, los pasos 3, 4, 7 y 8 pertenecen al orquestador.
Hermes no toca la tarea ni el índice y entrega el formato definido en
[`HERMES_TASK_GUIDE.md`](HERMES_TASK_GUIDE.md).

Si la tarea crea archivos nuevos, antes de `git diff --check` usa
`git add -N -- ruta1 ruta2` únicamente con las rutas permitidas. Esto añade
intención de seguimiento sin guardar contenido y evita que Git omita esos
archivos de la comprobación. Un comando obligatorio fallido impide pasar a
`review`, aunque otra variante del comando funcione.

Sólo puede existir un propietario por tarea. Si dos agentes intentan reclamarla,
el que observe un propietario previo se detiene y elige otra. Un agente puede
tomar una tarea abandonada únicamente si documenta el relevo en `Handoff` y
comprueba primero el estado real de los archivos.

## Cómo dejar una tarea bloqueada

`blocked` significa que continuar requiere información, autoridad o un cambio
externo específico. El agente debe registrar en `Handoff`:

- el bloqueo exacto;
- qué comprobó o intentó;
- qué falta para desbloquearlo;
- cuál es el siguiente paso seguro.

La dificultad, la falta de tiempo o una verificación todavía en ejecución no
son por sí mismas un bloqueo. En esos casos la tarea sigue `in_progress` y se
deja un traspaso.

## Cierre y definición de terminado

Una tarea sólo pasa de `review` a `done` cuando el auditor confirma que:

- todos los criterios de aceptación están satisfechos;
- las verificaciones indicadas se han ejecutado o su omisión está justificada;
- los archivos modificados están enumerados;
- no quedan decisiones ni errores ocultos;
- el documento refleja el resultado final, no el plan antiguo;
- `TASKS.md` coincide con la tarea.

El auditor repite los comandos literales desde el directorio declarado y
comprueba el diff, no sólo el resumen del ejecutor. Las afirmaciones del agente
son un handoff, no evidencia de aceptación.

Si la auditoría falla y quedan rondas, el orquestador conserva el candidato
permitido, pone en cuarentena los cambios fuera de alcance y devuelve los
fallos exactos a una nueva sesión. Después de la tercera ronda, repite esa
limpieza, marca `blocked`, limpia `Owner` y conserva candidato y artefactos para
comparación.

El resultado de una verificación se resume con evidencia corta: comando, estado
y dato relevante. Los logs completos deben permanecer fuera del documento.

## Reglas de documentación

- Usar lenguaje directo y frases cortas.
- Registrar hechos y decisiones, no narrar cada acción del agente.
- Usar fechas UTC en formato ISO 8601.
- No incluir secretos, claves, prompts, respuestas ni datos personales.
- No pegar salidas extensas; resumirlas y enlazar el artefacto si es necesario.
- Mantener cada tarea idealmente por debajo de 150 líneas.
- Añadir la información nueva al apartado correcto, no al final sin contexto.
- Si cambia una interfaz o la arquitectura, actualizar también `../README.md`.

## Orden de lectura para un agente nuevo

1. [`../README.md`](../README.md), para entender el producto.
2. Este documento, para entender el proceso.
3. [`TASKS.md`](TASKS.md), para ver el tablero actual.
4. La tarea elegida y los ficheros de sus dependencias.
5. Sólo después, los archivos de implementación relevantes.

Para Hermes, leer además [`HERMES_TASK_GUIDE.md`](HERMES_TASK_GUIDE.md) y no
leer auditorías antiguas salvo petición expresa del orquestador.

Este orden permite continuar el proyecto con contexto suficiente y evita que el
estado dependa de quién realizó el trabajo anterior.
