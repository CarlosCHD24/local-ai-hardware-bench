# TASK-001: Crear comprobador seguro de métricas

| Campo | Valor |
|---|---|
| Status | `ready` |
| Owner | — |
| Created | 2026-08-28T15:59:30Z |
| Updated | 2026-08-28T15:59:30Z |
| Depends on | — |

## Objetivo

Crear un comprobador Python sin dependencias externas que valide de forma
segura los endpoints `/health` y `/metrics` de `llama-server`.

## Contexto mínimo

- Leer `monitoring/AGENTS.md` y `monitoring/building/README.md`.
- El servidor exige `Authorization: Bearer` y nunca debe mostrarse la clave.
- Las métricas Prometheus de `llama.cpp` contienen `:` en sus nombres.

## Alcance

Incluye:

- `monitoring/check_llama_metrics.py` ejecutable con `python3 -m`.
- Pruebas unitarias en `monitoring/tests/test_check_llama_metrics.py`.
- Sólo biblioteca estándar de Python 3.10 o posterior.
- Base URL configurable, con `http://127.0.0.1:8080` por defecto.
- Clave desde `--api-key-file` o, si no se indica, `LOCAL_AI_API_KEY`.
- Timeout configurable y códigos de salida documentados en `--help`.

No incluye:

- Instalar Prometheus, Grafana o paquetes Python.
- Modificar o reiniciar `llama-server`.
- Persistir métricas ni calcular energía o costes.
- Cambiar archivos fuera de `monitoring/`, salvo el estado de esta tarea.

## Comportamiento requerido

- Considerar sano `/health` sólo con HTTP correcto y JSON `status: ok`.
- Verificar en `/metrics` las métricas de prompt, caché, generación,
  rendimiento y colas descritas en `monitoring/README.md`.
- Aceptar líneas Prometheus con etiquetas y omitir comentarios.
- Salir con `0` al validar, `2` ante configuración inválida, `3` ante fallo
  HTTP/red y `4` si falta una métrica requerida.
- Escribir errores breves en stderr sin incluir la clave ni cabeceras.

## Pasos

- [ ] Reclamar la tarea y actualizar `TASKS.md`.
- [ ] Implementar el comprobador.
- [ ] Añadir pruebas de éxito, configuración, fallo HTTP y métrica ausente.
- [ ] Ejecutar las verificaciones.
- [ ] Registrar resultado, archivos y estado final.

## Criterios de aceptación

- [ ] Funciona mediante `python3 -m monitoring.check_llama_metrics --help`.
- [ ] No añade dependencias ni contiene claves o direcciones privadas fijas.
- [ ] Las pruebas cubren los códigos de salida `0`, `2`, `3` y `4`.
- [ ] Una clave de prueba no aparece en stdout, stderr ni excepciones visibles.
- [ ] Todo el conjunto de pruebas existente sigue pasando.

## Verificación

```text
python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
python3 -m monitoring.check_llama_metrics --help
python3 -m pytest
git diff --check
```

Resultado: pendiente.

## Archivos permitidos

- `monitoring/check_llama_metrics.py`
- `monitoring/tests/test_check_llama_metrics.py`
- `monitoring/building/tasks/TASK-001-crear-comprobador-metricas.md`
- `monitoring/building/TASKS.md`

## Decisiones

- El comprobador se mantiene independiente de Prometheus para servir también
  como smoke test de despliegue.

## Handoff

Sin trabajo pendiente ni bloqueos.
