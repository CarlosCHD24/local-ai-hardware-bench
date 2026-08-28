# Auditoría de Hermes v2: TASK-001

## Resultado

- Veredicto: **no aceptado**.
- La tarea permanece `ready` en la rama del orquestador.
- Auditado: 2026-08-28T17:29:41Z.
- Candidato conservado en `honor-ai`, rama `hermes-task-001-v2`, worktree
  `/home/honor/.hermes/worktrees/local-ai-task-001-v2`.
- Base del candidato: `fa5caf5`.

Hermes produjo una implementación más cercana al contrato y reconoció el fallo
de sus tests. Sin embargo, cuatro de las ocho pruebas obligatorias fallan y el
candidato no satisface la definición de terminado.

## Configuración efectiva

- Hermes Agent 0.20.6; modelo Qwen 3.5 9B Q6_K (`local-agent`).
- Perfil dedicado `monitoringworker`, sin skills generales precargadas.
- `reasoning_config.enabled: false`, confirmado en la sesión.
- Máximo 12 iteraciones, 2.048 tokens por respuesta y 600 segundos por run.
- Contexto cliente 65.536; temperatura 0,1; `top_p` 0,95; `min_p` 0;
  semilla 42.
- Herramientas `terminal,file` y hard stop de bucles activado.

El modo one-shot no aplicó correctamente el directorio ni el límite de
iteraciones. La ejecución válida se realizó con `hermes chat --in ...
--max-turns 12 --run-budget 600 --reasoning none`.

## Verificación independiente

| Comprobación | Resultado |
|---|---|
| Preflight desde el worktree v2 | Pasa; Python 3.11.16 |
| Unit tests exactos desde la raíz | Falla: 8 ejecutados, 4 fallan |
| `python3 -m monitoring.check_llama_metrics --help` | Pasa, código 0 |
| `git diff --check` | Pasa, código 0 |
| `git status --short` | Sólo muestra las cuatro rutas permitidas |
| Estado y evidencias de la tarea | No completados; permanece `in_progress` |

## Hallazgos

### Críticos

1. Las pruebas de éxito, fallo HTTP, health inválido y métrica ausente no
   proporcionan una clave aislada. `main` devuelve `2` antes de ejercitar el
   comportamiento que esas pruebas afirman validar.
2. Los mocks de `urlopen` no modelan correctamente el context manager ni las
   respuestas consecutivas de `/health` y `/metrics`.
3. `check_health` y `check_metrics` usan siempre timeout `10`; la opción
   `--timeout` validada por `main` no se transmite.
4. Un fallo de red o HTTP al consultar `/metrics` acaba como código `4`, aunque
   el contrato reserva `4` para métricas ausentes y exige `3` para HTTP/red.

### Importantes

1. El test modifica `sys.path`, expresamente prohibido por la tarea.
2. La prueba de secreto no carga `testkey123` ni alcanza el fallo HTTP; por
   tanto todavía no demuestra redacción de credenciales.
3. El test de clave ausente borra directamente una variable del proceso en vez
   de aislarla con `mock.patch.dict`.
4. Hermes volvió a anteponer `|` adicionales a las tablas Markdown e inventó
   el timestamp redondo `18:00:00Z` en lugar de conservar el obtenido por
   `date -u`.
5. El resumen final afirma estado `review`, pero la tarea y el índice continúan
   en `in_progress`; no completó casillas ni evidencias.

## Aspectos positivos

- Trabajó finalmente en el worktree correcto y ejecutó el preflight.
- Creó exactamente los dos archivos Python previstos y no hizo commits.
- Incluyó las diez métricas correctas y los ocho nombres de prueba requeridos.
- No instaló paquetes, no usó el servidor real y no se observan secretos.
- A diferencia del primer piloto, declaró explícitamente que los tests fallan
  y dejó un handoff útil en vez de afirmar que habían pasado.
- El límite de 12 iteraciones detuvo el trabajo y forzó una entrega parcial.

## Telemetría y comparación

La sesión válida utilizó:

- unos 8 minutos de sesión en dos consultas, incluida una confirmación
  redundante solicitada por Hermes;
- 15 llamadas al modelo y 24 llamadas de herramienta;
- 26.042 tokens de entrada, 228.587 de caché y 12.021 de salida;
- 266.650 tokens contabilizados y 0 tokens de razonamiento registrados.

Frente al primer piloto, las llamadas bajaron de 66 a 15, la salida de 34.233 a
12.021 tokens y el tiempo aproximado de 20:16 a 8:04. La eficiencia y la
veracidad mejoraron, pero la aceptación funcional continúa fallando.

Hubo además dos invocaciones one-shot descartadas por una mala resolución del
directorio: una se detuvo sin modificar archivos y otra inspeccionó por error
el candidato v1. Sumadas, elevan el coste completo del experimento a 32 llamadas
y aproximadamente 12:53. No deben contarse como trabajo válido del candidato,
pero sí como coste de orquestación.

## Conclusión

La definición cerrada y `reasoning none` reducen mucho el bucle y mejoran la
honestidad del handoff. Para el siguiente piloto, la tarea ya incorpora un
patrón mínimo de mocks, aislamiento de entorno y propagación del timeout. Debe
mantenerse el perfil y usarse exclusivamente `hermes chat --in`; no se
recomienda aumentar otra vez los turnos antes de probar esa simplificación.
