# Diseño de tareas autónomas para Hermes

## Conclusión

Hermes funciona bien como ejecutor cuando la tarea elimina decisiones de
diseño, limita los archivos y convierte cada requisito en una comprobación.
No funciona bien como gestor de su propio proceso ni como auditor: en los
pilotos corrompió tablas, inventó evidencias y necesitó instrucciones literales
para corregir tests que afirmaba haber corregido.

La autonomía adecuada es técnica, no administrativa:

```text
diseñador publica --> orquestador fija commit --> Hermes implementa --> auditor acepta
```

Git es la fuente de verdad. Hermes no trabaja sobre “la última versión” de una
rama, sino sobre el `execution_commit` exacto autorizado en el manifiesto.

## Evidencia de los pilotos

| Variante | Primera entrega | Resultado final |
|---|---|---|
| Tarea abierta | 66 llamadas y 20:16 | Rechazada |
| Contrato cerrado | 15 llamadas y 8:04 | Rechazada, pero handoff veraz |
| Contrato más patrón de mocks | 12 llamadas y 4:39 | Candidato útil |
| v3 con devoluciones de auditoría | 47 llamadas acumuladas | Aceptada |

El patrón concreto redujo mucho la primera entrega. Las rondas posteriores se
consumieron principalmente en autocertificación, Markdown y tests mal
instrumentados, no en el código productivo.

## Perfil de una tarea apta

Una tarea para Hermes debe cumplir todo lo siguiente:

1. Un único resultado técnico y observable.
2. Máximo dos archivos de implementación. Hermes no duplica tests cuando el
   contrato inmutable ya cubre todos los comportamientos.
3. Todas las decisiones públicas ya cerradas: nombres, argumentos, formatos,
   errores y códigos de salida.
4. Preflight probado por el diseñador en el entorno del agente.
5. Sin instalación, despliegue, secretos reales ni servicios externos.
6. Entre cuatro y seis comportamientos verificables. Si hay más, se divide.
7. Tests de contrato inmutables, escritos por el diseñador y fuera de las
   rutas permitidas a Hermes.
8. Fixture literal cuando el test requiera Markdown, mocks, HTTP, tiempo o
   escritura atómica.
9. Comandos literales desde un directorio exacto, con código esperado.
10. Primera ronda de 12 iteraciones y 600 segundos; hasta dos correcciones de 8
    iteraciones y 360 segundos. Todas usan 2.048 tokens máximos de salida y
    timeout externo de 720 o 480 segundos respectivamente.
11. Estado final del ejecutor: `PASS` o `FAIL`; nunca `done`.

Si una tarea incumple uno de estos puntos, el diseñador debe dividirla o
dejarla en `draft`.

## Responsabilidades fuera de Hermes

El orquestador debe:

- publicar primero documentación, tareas y contratos en `base_commit`;
- crear una rama y un worktree exclusivos desde `base_commit`;
- comprobar el preflight antes de reclamar la tarea;
- ejecutar también el preflight literal de cada tarea sobre una rama limpia y
  detenerse si el baseline ya falla;
- reclamar la tarea, crear `execution_commit` y publicar la rama limpia;
- generar el manifiesto desde `JOB_MANIFEST_TEMPLATE.md`;
- exigir el proveedor y modelo locales y prohibir fallback externo;
- mantener estados y timestamps sin delegarlos en Hermes;
- invocar el perfil y directorio correctos;
- conservar telemetría y candidato;
- ejecutar la auditoría independiente después de cada ronda, aunque la salida
  de Hermes esté truncada o no contenga `PASS`;
- ejecutar todas las comprobaciones aunque ya exista un path prohibido y
  acumular sus códigos, sin usar sólo el resultado del último comando;
- eliminar mecánicamente espacios finales antes de auditar;
- devolver a Hermes únicamente los errores del auditor y permitir como máximo
  dos rondas correctivas;
- repetir al final del log un resumen de tests fallidos y rutas prohibidas para
  que nunca desaparezcan al truncar la evidencia;
- mover a cuarentena los artefactos fuera de alcance entre rondas, conservando
  una copia en el directorio del job;
- crear y publicar `accepted_commit` sólo tras la auditoría;
- cambiar `review` y `done`.

En modo `orchestrated`, Hermes no modifica los documentos de workflow de
`building/`, no inventa timestamps y no resume el tablero. Esto elimina trabajo
que no aporta al producto y que el modelo local realizó de forma poco fiable.

## Contrato de ejecución

Configuración base:

```text
profile: monitoringworker
provider: custom:local-ai (obligatorio)
model: local-agent (obligatorio)
fallback: disabled
reasoning: none
max_turns: 12
run_budget_seconds: 600
external_timeout_seconds: 720
repair_max_turns: 8
repair_budget_seconds: 360
repair_timeout_seconds: 480
max_tokens: 2048
toolsets: terminal,file
working_directory: raíz del worktree
job_manifest: ruta absoluta generada por el orquestador
```

Antes de reclamar la tarea, el orquestador valida desde el mismo entorno
desacoplado: Git remoto accesible, baseline limpio, ruta del ejecutable, clave
no vacía, autenticación contra `/v1/models`, una inferencia mínima y ausencia
de fallback. Cualquier discrepancia Git, `401`, cambio de proveedor o fallo de
inferencia detiene el trabajo sin reclamarlo.

Después reclama la tarea en la rama exclusiva, crea y publica
`execution_commit` y genera el manifiesto. No inicia Hermes hasta que la
referencia remota de la rama coincide con ese commit.

Usar `hermes chat --in`; el modo one-shot no respetó de forma fiable el
directorio ni el límite de iteraciones durante el piloto.

La petición debe ordenar ejecutar sin pedir confirmación. La primera herramienta
es `pwd`; después Hermes ejecuta el bloque Git exacto del manifiesto: `fetch` y
verificación de raíz, rama, `HEAD`, referencia remota, ascendencia y limpieza.
Si algo no coincide, devuelve `CONFIG_ERROR` y no usa `pull`, cambia de rama,
resuelve conflictos ni busca otros repositorios o worktrees.

La credencial de Hermes es de sólo lectura. Los commits, pushes y fusiones se
ejecutan fuera del modelo por el orquestador.

## Scripts operativos

- `monitoring/scripts/prepare_hermes_task.sh` hace `fetch`, exige que la rama
  remota coincida con `base_commit`, crea rama y worktree, reclama la tarea,
  publica `execution_commit` y genera el manifiesto.
- `monitoring/scripts/run_hermes_sequence.sh` actúa como worker de una única
  tarea ya preparada: vuelve a verificar el manifiesto, ejecuta hasta tres
  rondas, audita, crea el commit final y lo publica.
- `monitoring/scripts/orchestrate_hermes_sequence.sh` encadena TASK-002 a
  TASK-005. Cada tarea nueva parte del `accepted_commit` de la anterior.

El preparador y el worker se ejecutan como procesos del orquestador, no como
herramientas decididas por el modelo. Hermes recibe únicamente el worktree, el
manifiesto y el prompt de su tarea.

Todos los `fetch` usan un refspec explícito de la rama autorizada. El flujo no
depende de que `remote.origin.fetch` incluya todas las ramas.

## Salida final obligatoria

Hermes devuelve únicamente evidencia breve:

```text
RESULT: PASS | FAIL | CONFIG_ERROR
CWD: ruta real
BASE_COMMIT: SHA recibido
EXECUTION_COMMIT: SHA verificado
FILES: rutas modificadas
CHECKS:
- comando literal | código | resumen
PENDING: none | descripción concreta
```

`PASS` sólo es válido si todos los comandos obligatorios terminaron con el
código esperado. Un comando alternativo no sustituye al definido. La decisión
de avanzar depende de los tests de contrato y de la auditoría del orquestador,
no de poder analizar este texto.

## Rondas y recuperación

Cada ronda parte de los archivos permitidos conservados y de un prompt nuevo.
Las rondas correctivas no releen documentación general ni reescriben archivos
completos; reciben sólo el candidato y un máximo de 100 líneas de auditoría. El
resumen estructurado se coloca al final para incluir siempre tests fallidos y
rutas prohibidas. Estas últimas se guardan en cuarentena antes del siguiente
intento para que no contaminen la reparación. Tras cada salida, el orquestador
ejecuta siempre las verificaciones inmutables:

1. Si pasan, el auditor marca `done`; el orquestador crea y publica
   `accepted_commit` y habilita la dependencia.
2. Si fallan y quedan rondas, entrega a Hermes el resumen literal de fallos.
3. Tras tres rondas fallidas, pone en cuarentena cualquier cambio prohibido,
   marca `blocked`, limpia `Owner` y conserva código permitido, evidencias y
   logs para auditoría.

El presupuesto interno no interrumpe necesariamente una inferencia en curso; el
timeout externo es el único límite fuerte de tiempo de pared y prevalece. Nunca
se reanuda una sesión que haya usado un proveedor distinto del local
configurado.

Antes de una ronda correctiva se repiten `fetch` y las comprobaciones de rama y
SHA, pero el worktree puede contener únicamente el candidato permitido. Si la
rama remota avanzó, el job se detiene; no integra cambios nuevos a mitad de una
tarea. La siguiente tarea se crea desde `accepted_commit` en una rama nueva.

### Puerta de reparación

Antes de modificar el candidato, Hermes ejecuta el test de contrato afectado y
trabaja sobre su salida real. Después de cada edición ejecuta `py_compile` para
Python y repite ese mismo contrato. No puede declarar una corrección sin un
código `0` observado en la ronda actual.

Una segunda ronda debe abordar una causa raíz distinta de la primera. Si la
firma de auditoría se repite dos veces, el orquestador bloquea y escala al
diseñador en vez de consumir una tercera ronda idéntica. El handoff conserva
el test fallido, la hipótesis descartada y el esqueleto o división necesarios.

Para una operación sobre dos archivos, un fallo simulado de escritura o un
rollback, la tarea debe aportar un protocolo literal y contratos separados por
transición. Sin ellos permanece `draft`; no se usa Hermes para descubrir el
diseño durante la ejecución.

## Qué trabajo asignar

Adecuado sin ayuda adicional:

- funciones Python con biblioteca estándar;
- parsers con entradas y salidas cerradas;
- CLI pequeñas;
- reglas deterministas y tests con fixtures;
- validadores de archivos del repositorio.

Adecuado sólo con esqueleto o ejemplo:

- mocks con varias respuestas;
- escritura atómica;
- servidores HTTP;
- formatos YAML o Prometheus;
- sincronización de varios documentos.

No asignar como una sola tarea autónoma:

- investigación más implementación;
- selección de arquitectura o producto;
- instalación y despliegue;
- cambios con secretos reales;
- modificación de servicios en ejecución;
- aceptación de su propio resultado.

## Regla para ampliar el backlog

Sólo se prepara el siguiente grupo de tareas cuando sus herramientas de
verificación existen. Si falta `promtool`, una imagen o una decisión de
despliegue, esas tareas permanecen fuera de `ready`; no se sustituye la
validación semántica por búsquedas de texto débiles.
