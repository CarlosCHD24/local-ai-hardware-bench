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
6. Matriz requisito → test → resultado esperado.
7. Fixture o patrón mínimo cuando el test requiera mocks, HTTP, tiempo o
   escritura atómica.
8. Comandos literales desde un directorio exacto, con código esperado.
9. Presupuesto predeterminado: 12 iteraciones, 600 segundos y 2.048 tokens de
   salida por llamada.
10. Estado final del ejecutor: `PASS` o `FAIL`; nunca `done`.

Si una tarea incumple uno de estos puntos, el diseñador debe dividirla o
dejarla en `draft`.

## Responsabilidades fuera de Hermes

El orquestador debe:

- crear y fijar el worktree;
- comprobar el preflight;
- reclamar la tarea y actualizar timestamps;
- invocar el perfil y directorio correctos;
- conservar telemetría y candidato;
- ejecutar la auditoría independiente;
- cambiar `review` y `done`.

En modo `orchestrated`, Hermes no modifica los documentos de workflow de
`building/`, no inventa timestamps y no resume el tablero. Esto elimina trabajo
que no aporta al producto y que el modelo local realizó de forma poco fiable.

## Contrato de ejecución

Configuración base:

```text
profile: monitoringworker
reasoning: none
max_turns: 12
run_budget_seconds: 600
max_tokens: 2048
toolsets: terminal,file
working_directory: raíz del worktree
```

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
código esperado. Un comando alternativo no sustituye al definido.

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
