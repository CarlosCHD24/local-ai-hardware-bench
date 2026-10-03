# Plan de monitoring y preflight

## Contexto

La rama `hermes/preflight-hardening` (commit `89dbffe`) importó el WIP de Codex del sistema de monitoring.
Ese trabajo cubre el tablero de tareas TASK-004..TASK-024 y los colectores NVIDIA.
Incluye la integración con prometheus/grafana/systemd y los `contract_tests`.
También incorpora `preflight.py` como comprobación de sólo lectura del host.
Esta máquina de desarrollo no tiene GPU, por lo que las verificaciones dependientes de NVIDIA no son ejecutables aquí.

## Estado del tablero

| tarea | estado declarado |
|---|---|
| TASK-004 | `done` |
| TASK-005 | `done` |
| TASK-006 | `done` |
| TASK-007 | `done` |
| TASK-008 | `done` |
| TASK-009 | `done` |
| TASK-010 | `done` |
| TASK-011 | `done` |
| TASK-012 | `done` |
| TASK-013 | `done` |
| TASK-014 | `done` |
| TASK-015 | `done` |
| TASK-016 | `done` |
| TASK-017 | `done` |
| TASK-018 | `done` |
| TASK-019 | `ready` |
| TASK-020 | `draft` |
| TASK-021 | `draft` |
| TASK-022 | `draft` |
| TASK-023 | `draft` |
| TASK-024 | `draft` |

## Verificaciones (Torno 2)

Ejecutado sobre la rama `hermes/preflight-hardening`, con `.venv` recien creado
(`python3 -m venv .venv`, `pip install pytest pyyaml`). Sin GPU ni `nvidia-smi`
en la maquina de desarrollo.

### a) Tests -> resultado

Comando base: `.venv/bin/python -m pytest monitoring/tests monitoring/contract_tests -q --no-header -o 'testpaths='`

| fichero de test | recogidos | resultado |
|---|---|---|
| `monitoring/tests/test_check_llama_metrics.py` | 10 | 10 passed |
| `monitoring/contract_tests/test_markdown_table_contract.py` | 5 | 5 passed (+4 subtests) |
| `monitoring/contract_tests/test_nvidia_metrics_contract.py` | 5 | 5 passed (+6 subtests) |
| `monitoring/contract_tests/test_nvidia_textfile_contract.py` | 3 | 3 passed |
| `monitoring/contract_tests/test_prometheus_files_contract.py` | 2 | 2 passed |
| `monitoring/contract_tests/test_taskctl_contract.py` | 6 | 6 passed (+5 subtests) |
| `monitoring/contract_tests/test_taskctl_transitions_contract.py` | 5 | 5 passed |
| **Total** | **36** | **36 passed, 15 subtests passed, 0 failed, 0 errors** |

Validadores sueltos sin GPU:

| validador | comando | resultado |
|---|---|---|
| `monitoring/validate_prometheus.py` | `.venv/bin/python monitoring/validate_prometheus.py --config monitoring/prometheus/prometheus.yml` | OK (exit 0, sin salida) |
| `monitoring/preflight.py` | `.venv/bin/python monitoring/preflight.py` | Falla por hardware ausente (exit 1) |

### b) Fallos reales

Ninguno. No hay `FAILED` ni `ERROR` en pytest, ni errores en `validate_prometheus.py`.

### c) Fallos por ausencia de GPU

| item | sintoma | localizacion |
|---|---|---|
| `monitoring/preflight.py` | `missing: nvidia-smi` (exit 1) | `monitoring/preflight.py:9-10` (lista `REQUIRED` en `monitoring/preflight.py:5`) |

La maquina no tiene `nvidia-smi` (`which nvidia-smi` -> no encontrado). Es una falla
del entorno, no del codigo. Los tests de contrato NVIDIA pasan porque usan mocks/fixtures
sin requerir GPU real.

### d) Como reproducir

```sh
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml
.venv/bin/python -m pytest monitoring/tests monitoring/contract_tests -q --no-header -o 'testpaths='
.venv/bin/python monitoring/validate_prometheus.py --config monitoring/prometheus/prometheus.yml
.venv/bin/python monitoring/preflight.py   # esperado: falla con 'missing: nvidia-smi' si no hay GPU
```

## Analisis de preflight.py

Hoy `monitoring/preflight.py` sólo comprueba con `shutil.which` que existan
`systemctl` y `nvidia-smi`; no ejecuta ninguno, no valida artefactos, listeners
ni estado del stack, y no distingue host de desarrollo de servidor. Se ejecuta
sin argumentos y devuelve 1 en cuanto falta un binario, aunque el resto del
monitoring pueda estar correcto.

Lagunas concretas:

1. No comprueba que `nvidia-smi` **funcione**: no lanza
   `--query-gpu=...` ni verifica que haya GPUs reales o que el adaptador
   (`monitoring/nvidia_textfile.py`) escriba una muestra válida.
2. No verifica listeners ni puertos: 9100 (node_exporter), 9090 (Prometheus) y
   3000 (Grafana), ni que estén en `127.0.0.1` y no en `0.0.0.0`.
3. No valida el textfile collector: existencia/permisos de
   `/var/lib/node_exporter/textfile_collector`, frescura de
   `local_ai_nvidia.prom` ni que sea parseable con `local_ai_gpu_scrape_success 1`.
4. No valida Prometheus real: `rule_files` existentes, sintaxis de reglas ni
   scrape config; `validate_prometheus.py` sólo busca substrings en el texto.
5. No invoca `validate_operation.py` ni `systemd-analyze verify` sobre las
   unidades (rutas, flag loopback, cadencia 15 s) que exige TASK-018.
6. No distingue **host de despliegue vs servidor de inferencia**
   (`192.168.3.42:8080`): en dev falla por ausencia de GPU sin poder validar el
   resto; no hay perfiles (`dev`/`server`) ni salida estructurada.
7. No es parametrizable ni testeable: sin `--json`, sin severidades y sin tests
   propios fuera de `contract_tests/`.

Contratos/tests contra los que debe validarse (sin modificarlos):

- `monitoring.contract_tests.test_prometheus_files_contract` (loopback 9100 y
  textfile collector) y `test_nvidia_textfile_contract` (semántica éxito/fallo).
- `monitoring.validate_prometheus` (scrape config) y `monitoring.validate_operation`
  (unidades TASK-015/TASK-016).
- TASK-010 (node_exporter `127.0.0.1:9100` + collector), TASK-015/TASK-016
  (oneshot y timer de 15 s), TASK-018 (validador de unidades) y TASK-020
  (frescura del colector NVIDIA).

## Plan de accion

1. **Perfilar y endurecer `preflight.py`**
   - Archivos: `monitoring/preflight.py` (perfiles `--profile dev|server`,
     `--json`, mensajes por check).
   - Verificación: `.venv/bin/python monitoring/preflight.py --profile dev`
     -> exit 0 sin GPU; en la RTX 3060 `python3 monitoring/preflight.py
     --profile server` -> exit 0.
   - Riesgo: que el perfil `dev` oculte fallos reales; `server` debe ser
     estricto (GPU y servicios obligatorios) y `dev` sólo relajar NVIDIA.

2. **Comprobar listeners y loopback (9100/9090/3000)**
   - Archivos: `monitoring/check_listeners.py` (nuevo, sólo lectura de
     `/proc/net/tcp`), `monitoring/deployment.md`.
   - Verificación: `.venv/bin/python monitoring/check_listeners.py --require
     127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000`.
   - Riesgo: falsos negativos si los servicios aún no están arrancados; dejar
     severidad no bloqueante hasta TASK-019.

3. **Validar el textfile collector NVIDIA (frescura y contenido)**
   - Archivos: `monitoring/check_nvidia_textfile.py` (nuevo, reutiliza
     `nvidia_textfile.NAME`), `monitoring/preflight.py`.
   - Verificación: `.venv/bin/python monitoring/check_nvidia_textfile.py
     --directory /var/lib/node_exporter/textfile_collector --max-age 45`.
   - Riesgo: umbral de frescura frente al timer de 15 s; documentar el margen y
     usar `local_ai_gpu_scrape_success` como señal principal.

4. **Integrar validadores existentes y herramientas reales**
   - Archivos: `monitoring/preflight.py`, `monitoring/deployment.md`.
   - Verificación: `promtool check config monitoring/prometheus/prometheus.yml`
     y `systemd-analyze verify monitoring/systemd/*.service
     monitoring/systemd/*.timer`; si la herramienta no está en dev, degradar a
     warning.
   - Riesgo: depender de binarios ausentes en desarrollo; nunca debe romper
     `--profile dev`.

5. **Añadir tests de preflight (fuera de `contract_tests/`)**
   - Archivos: `monitoring/tests/test_preflight.py`,
     `monitoring/tests/test_check_nvidia_textfile.py`.
   - Verificación: `.venv/bin/python -m pytest monitoring/tests -q
     --no-header -o 'testpaths='`.
   - Riesgo: duplicar los contratos inmutables; no tocar
     `monitoring/contract_tests/`.

## Progreso de implementacion

> Normas del proyecto para este plan (autorizadas por CarlosCHD24, 2026-10-03):
> Pi y Hermes pueden hacer `git commit` en RAMAS DE TRABAJO (nunca en `main`,
> nunca push a `main`). Tras cada paso verificado (pytest en verde + comprobacion
> del director), el director commitea el paso con mensaje descriptivo.
> Siguen vigentes: no tocar `monitoring/contract_tests/`, no modificar el
> servidor de inferencia, no guardar claves.

| paso | estado |
|---|---|
| importar WIP de monitoring (TASK-004..024) | hecho |
| verificaciones (tests + validadores sin GPU, Torno 2) | hecho |
| analisis de preflight.py (ambito vs TASK-010/015/016/018 y deployment) | hecho |
| 1. perfilar y endurecer preflight (dev/server, --json) | hecho |
| 2. comprobar listeners 9100/9090/3000 en loopback | hecho (torno 5: `check_listeners.py` + 9 tests) |
| 3. validar textfile collector NVIDIA (frescura/contenido) | pendiente |
| 4. integrar validadores y promtool/systemd-analyze | pendiente |
| 5. tests de preflight fuera de `contract_tests/` | hecho (torno 4: `test_preflight.py`, 9 tests) |

### Verificación del paso 1 (Torno 4)

`monitoring/preflight.py` admiten ahora `--profile dev|server` (por defecto
`server`, para conservar la semántica estricta previa) y `--json`. Cada check
emite su propio mensaje y estado (`ok`/`warning`/`error`): `systemctl` es
obligatorio en ambos perfiles y `nvidia-smi` sólo bloquea en `server`.

Comandos ejecutados:

```sh
.venv/bin/python monitoring/preflight.py --profile dev     # exit 0 sin GPU
.venv/bin/python monitoring/preflight.py --profile server  # exit 1 sin GPU
.venv/bin/python monitoring/preflight.py --profile dev --json  # JSON válido
.venv/bin/python -m pytest monitoring/tests monitoring/contract_tests -q --no-header -o 'testpaths='
```

Resultado del pytest: **45 passed, 15 subtests passed, 0 failed, 0 errors**
(36 tests previos + 9 nuevos en `monitoring/tests/test_preflight.py`). Las
comprobaciones sin GPU se simulan inyectando un `shutil.which` falso, por lo que
no dependen del hardware. No se ha modificado `monitoring/contract_tests/`.

### Verificación del paso 2 (Torno 5)

`monitoring/check_listeners.py` (nuevo, sólo stdlib) parsea `/proc/net/tcp`,
extrae las direcciones locales en estado `LISTEN` y compara con la lista de
`--require host:puerto,...`. Emite un mensaje por listener (`presente`/`falta`),
soporta `--json` y `--proc PATH`, y devuelve 0 si todos están presentes o 1 si
falta alguno. Un bind en `0.0.0.0` no satisface un requisito `127.0.0.1`.

Integración en `monitoring/preflight.py`: `--require-listeners` importa
directamente `check_listeners` (sin subprocess) y añade un check por listener a
la salida de texto y JSON, sin alterar los perfiles `dev`/`server`.

Comandos ejecutados:

```sh
.venv/bin/python monitoring/check_listeners.py --require 127.0.0.1:9100          # exit 1, 'falta'
.venv/bin/python monitoring/preflight.py --profile dev --require-listeners 127.0.0.1:9100
.venv/bin/python -m pytest monitoring/tests monitoring/contract_tests -q --no-header -o 'testpaths='
```

Resultado del pytest: **54 passed, 15 subtests passed, 0 failed, 0 errors**
(45 previos + 9 nuevos en `monitoring/tests/test_check_listeners.py`). No se ha
modificado `monitoring/contract_tests/`.
