# Auditoría de Hermes v3: TASK-001

## Resultado

- Veredicto: **aceptado con correcciones mecánicas del auditor**.
- Auditado: 2026-08-28T21:19:48Z.
- Candidato conservado en `honor-ai`, rama `hermes-task-001-v3`, worktree
  `/home/honor/.hermes/worktrees/local-ai-task-001-v3`.
- Base del candidato: `984c5ba`.
- Integrado en la rama local del orquestador.

Hermes implementó el comprobador y convergió después de varias devoluciones de
auditoría. El auditor sólo eliminó espacios finales y corrigió el parámetro
`fp` de un `HTTPError` de prueba; no modificó el código productivo.

## Configuración efectiva

- Hermes Agent 0.20.6; Qwen 3.5 9B Q6_K (`local-agent`).
- Perfil dedicado `monitoringworker`.
- `reasoning_config.enabled: false` y 0 tokens de razonamiento registrados.
- 12 iteraciones por run, 2.048 tokens por respuesta y 600 segundos.
- Contexto cliente 65.536; temperatura 0,1; `top_p` 0,95; `min_p` 0;
  semilla 42.
- Herramientas `terminal,file`; hard stop de bucles activado.

## Verificación independiente final

| Comprobación | Resultado |
|---|---|
| Preflight en el worktree v3 | Pasa; Python 3.11.16 |
| Unit tests desde la raíz y sin clave en entorno | 10 pasan, código 0 |
| Ayuda mediante `python3 -m` | Pasa, código 0 |
| `git diff --check`, incluyendo archivos nuevos | Pasa, código 0 |
| `git status --short` | Sólo las cuatro rutas permitidas |
| Estado e índice | `review`, sin owner y coherentes |
| Smoke test autenticado contra `llama-server` | Pasa: health y métricas válidos |

La inspección confirmó las diez métricas, etiquetas Prometheus, propagación del
timeout, autenticación Bearer, códigos `0`, `2`, `3` y `4`, separación entre
fallos de transporte y métricas ausentes, y redacción de excepciones.

## Evolución del candidato

1. La primera entrega v3 produjo código útil y 10 tests, pero agotó el límite
   antes de cerrar las verificaciones.
2. La auditoría detectó clasificación incorrecta de errores de `/metrics`, uso
   prohibido de `sys.path`, pruebas de secreto falsas y metadatos incoherentes.
3. Hermes corrigió el código productivo y los tests tras devoluciones concretas.
4. Necesitó microtareas adicionales para hacer que cada test capturase una sola
   invocación y para completar la documentación.
5. El auditor aplicó dos ajustes mecánicos finales: espacios y argumento `fp`
   de un `HTTPError` de prueba.

## Telemetría

La primera entrega v3 necesitó aproximadamente 4:39, 12 llamadas al modelo y
5.171 tokens de salida. El contrato con patrón de mocks redujo a la mitad el
tiempo de la entrega inicial respecto de v2.

La sesión completa, incluidas cuatro rondas de devolución, acumuló:

- 47 llamadas al modelo y 71 llamadas de herramienta;
- 91.810 tokens de entrada, 1.552.268 de caché y 18.537 de salida;
- 1.662.615 tokens contabilizados;
- unos 18:47 de sesión, de los que aproximadamente 14:27 fueron ejecuciones de
  Hermes.

## Comparación

| Piloto | Resultado | Llamadas | Salida | Tiempo aproximado |
|---|---|---:|---:|---:|
| v1 | Rechazado | 66 | 34.233 | 20:16 |
| v2, sesión válida | Rechazado | 15 | 12.021 | 8:04 |
| v3, primera entrega | Parcial útil | 12 | 5.171 | 4:39 |
| v3, sesión completa | Aceptado | 47 | 18.537 | 18:47 |

## Conclusión

La tarea cerrada y `reasoning none` mejoraron mucho la primera entrega y la
honestidad del agente. El modelo local puede ejecutar tareas acotadas, pero no
es fiable como autocertificador: repitió afirmaciones que el diff desmentía y
necesitó instrucciones casi literales para corregir tests. El patrón adecuado
es Hermes como ejecutor económico, límites estrictos y auditor independiente.
