# Diseño de tareas autónomas para Hermes

## Conclusión

Hermes funciona bien como ejecutor cuando la tarea elimina decisiones de
diseño, limita los archivos y convierte cada requisito en una comprobación.
No funciona bien como gestor de su propio proceso ni como auditor: en los
pilotos corrompió tablas, inventó evidencias y necesitó instrucciones literales
para corregir tests que afirmaba haber corregido.

La autonomía adecuada es técnica, no administrativa:

```text
orquestador prepara --> Hermes implementa y verifica --> auditor decide
```

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
2. Máximo dos archivos de implementación y un archivo de pruebas.
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
10. Hasta tres rondas independientes de 12 iteraciones, 600 segundos y 2.048
    tokens de salida por llamada; timeout externo de 720 segundos por ronda.
11. Estado final del ejecutor: `PASS` o `FAIL`; nunca `done`.

Si una tarea incumple uno de estos puntos, el diseñador debe dividirla o
dejarla en `draft`.

## Responsabilidades fuera de Hermes

El orquestador debe:

- crear y fijar el worktree;
- comprobar el preflight antes de reclamar la tarea;
- exigir el proveedor y modelo locales y prohibir fallback externo;
- reclamar la tarea y actualizar timestamps;
- invocar el perfil y directorio correctos;
- conservar telemetría y candidato;
- ejecutar la auditoría independiente después de cada ronda, aunque la salida
  de Hermes esté truncada o no contenga `PASS`;
- devolver a Hermes únicamente los errores del auditor y permitir como máximo
  dos rondas correctivas;
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
max_tokens: 2048
toolsets: terminal,file
working_directory: raíz del worktree
```

Antes de modificar el tablero, el orquestador valida desde el mismo entorno
desacoplado: ruta absoluta del ejecutable, clave no vacía, autenticación contra
`/v1/models`, una inferencia mínima y ausencia de fallback. Cualquier `401`,
cambio de proveedor o fallo de inferencia detiene el trabajo sin reclamarlo.

Usar `hermes chat --in`; el modo one-shot no respetó de forma fiable el
directorio ni el límite de iteraciones durante el piloto.

La petición debe ordenar ejecutar sin pedir confirmación. La primera herramienta
es `pwd`. Si no coincide con la raíz autorizada, Hermes devuelve `CONFIG_ERROR`
y no busca otros repositorios o worktrees.

## Salida final obligatoria

Hermes devuelve únicamente evidencia breve:

```text
RESULT: PASS | FAIL | CONFIG_ERROR
CWD: ruta real
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

Cada ronda parte de los archivos conservados y de un prompt nuevo. Tras cada
salida, el orquestador ejecuta siempre las verificaciones inmutables:

1. Si pasan, marca `done`, crea un commit de control y habilita la dependencia.
2. Si fallan y quedan rondas, entrega a Hermes el resumen literal de fallos.
3. Tras tres rondas fallidas, marca `blocked`, limpia `Owner` y conserva código,
   pruebas y logs para auditoría.

El timeout externo prevalece sobre el presupuesto interno. Nunca se reanuda una
sesión que haya usado un proveedor distinto del local configurado.

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
