# TASK-001: Crear comprobador seguro de métricas

| Campo | Valor |
|---|---|
| Status | `done` |
| Owner | — |
| Created | 2026-08-28T15:59:30Z |
| Updated | 2026-08-28T21:19:48Z |
| Depends on | — |

## Resultado que debes entregar

Dos archivos Python, sin dependencias externas, que permitan ejecutar desde la
raíz del repositorio:

```text
python3 -m monitoring.check_llama_metrics [opciones]
python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
```

El primer comando valida `/health` y `/metrics` de `llama-server`. El segundo
debe terminar con código `0` y probar todos los casos de la matriz inferior.

## Preflight obligatorio

Antes de modificar archivos, ejecuta desde la raíz del repositorio:

```text
pwd
git rev-parse --show-toplevel
python3 --version
python3 -c "import argparse, json, unittest, urllib.request"
```

Continúa sólo si los dos primeros comandos muestran el mismo directorio, Python
es 3.10 o posterior y el último comando termina con código `0`. No instales ni
intentes usar `pytest`. Si falla el preflight, no programes: deja la tarea en
`ready` y registra el comando fallido como `NO EJECUTADO` en `Handoff`.

## Contrato cerrado

Implementa `monitoring/check_llama_metrics.py` con biblioteca estándar:

- Punto de entrada `main(argv=None) -> int` y ejecución mediante `python3 -m`.
- Opciones exactas: `--base-url`, `--api-key-file` y `--timeout`.
- URL predeterminada: `http://127.0.0.1:8080`; acepta una `/` final.
- Timeout predeterminado positivo. Un timeout `<= 0` devuelve código `2`.
- Si se indica `--api-key-file`, lee y recorta ese fichero. En otro caso usa
  `LOCAL_AI_API_KEY`. Una clave ausente o vacía devuelve código `2`.
- Envía `Authorization: Bearer <clave>` a ambos endpoints.
- `/health` sólo es válido con HTTP 2xx, JSON válido y `status == "ok"`.
- Cualquier fallo de red, HTTP, lectura o respuesta health inválida devuelve
  código `3`.
- `/metrics` debe contener las diez métricas exactas de la lista inferior. Si
  falta alguna, devuelve código `4`.
- El código `4` sólo se usa después de recibir y analizar `/metrics`; un fallo
  HTTP o de red en ese endpoint también devuelve `3`.
- Pasa el valor de `--timeout` a las dos llamadas de `urlopen`; no lo fijes en
  funciones auxiliares.
- En éxito devuelve `0` y escribe un mensaje breve en stdout.
- Los errores se escriben en stderr. Nunca muestres la clave ni cabeceras.

Métricas obligatorias:

```text
llamacpp:prompt_tokens_total
llamacpp:prompt_tokens_cached_total
llamacpp:tokens_predicted_total
llamacpp:prompt_seconds_total
llamacpp:tokens_predicted_seconds_total
llamacpp:prompt_tokens_seconds
llamacpp:predicted_tokens_seconds
llamacpp:requests_processing
llamacpp:requests_deferred
llamacpp:n_tokens_max
```

Al analizar Prometheus, ignora líneas vacías y comentarios. Considera nombre de
métrica el texto anterior a `{` o al primer espacio; por tanto debes aceptar
líneas con etiquetas como `llamacpp:requests_processing{slot="0"} 1`.

## Matriz mínima de pruebas

Crea `monitoring/tests/test_check_llama_metrics.py` usando `unittest` y
`unittest.mock`. Importa siempre con:

```python
from monitoring import check_llama_metrics
```

No alteres `sys.path`, no accedas a la red real y no leas claves reales.

| Prueba | Comportamiento que debe demostrar |
|---|---|
| `test_success_returns_0_and_accepts_labels` | Health válido y las 10 métricas, incluyendo una con etiquetas, devuelven `0` |
| `test_missing_key_returns_2` | Sin fichero ni variable de entorno devuelve `2` |
| `test_empty_key_file_returns_2` | Un fichero vacío devuelve `2` |
| `test_non_positive_timeout_returns_2` | Timeout cero o negativo devuelve `2` |
| `test_http_failure_returns_3_without_secret` | Fallo HTTP devuelve `3`; la clave de prueba no aparece en stdout ni stderr |
| `test_invalid_health_returns_3` | JSON inválido o status distinto de ok devuelve `3` |
| `test_missing_metric_returns_4` | Respuesta válida sin `requests_deferred` devuelve `4` |
| `test_required_metric_catalog_is_exact` | El catálogo contiene exactamente las 10 métricas indicadas |

Cada prueba de código de salida debe invocar comportamiento real de `main`; no
se acepta comprobar sólo una constante ni ignorar el código devuelto.

Usa este patrón mínimo para aislar entorno y respuestas. Puedes ampliarlo, pero
no reemplazarlo por `sys.path` ni por acceso de red:

```python
class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status = body.encode(), status
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body

with mock.patch.dict(os.environ, {"LOCAL_AI_API_KEY": "testkey123"}, clear=True), \
     mock.patch("monitoring.check_llama_metrics.urllib.request.urlopen",
                side_effect=[FakeResponse(health), FakeResponse(metrics)]) as urlopen:
    result = check_llama_metrics.main(["--timeout", "7"])
```

En el test de éxito comprueba además que ambas llamadas recibieron `timeout=7`.
Para la clave vacía crea un fichero temporal real con `tempfile`; no simules una
función auxiliar. Cada test debe aislar `os.environ` con `mock.patch.dict`.

## Archivos permitidos

- `monitoring/check_llama_metrics.py`
- `monitoring/tests/test_check_llama_metrics.py`
- Este documento: únicamente estado, owner, `Updated`, casillas y evidencias.
- `monitoring/building/TASKS.md`: únicamente estado, owner y próxima tarea.

No crees otros archivos, no instales paquetes, no uses el servidor real y no
hagas `commit`, `push` ni cambios fuera del worktree.

## Secuencia de trabajo

- [x] Ejecutar el preflight.
- [x] Cambiar la tarea y el índice a `in_progress`, con Owner `Hermes-v2` y una
      hora obtenida mediante `date -u`; no inventar timestamps.
- [x] Implementar únicamente los dos archivos Python permitidos.
- [x] Ejecutar los cuatro comandos de verificación exactamente como aparecen.
- [x] Si todos pasan, marcar las casillas y dejar la tarea en `review`, sin
      owner. Nunca marcar `done`.

## Verificación obligatoria desde la raíz

| Comando exacto | Código esperado |
|---|---:|
| `python3 -m unittest discover -s monitoring/tests -p 'test_*.py'` | `0` |
| `python3 -m monitoring.check_llama_metrics --help` | `0` |
| `git diff --check` | `0` |
| `git status --short` | `0`; sólo rutas permitidas |

No sustituyas estos comandos por otros. Si alguno no puede ejecutarse o falla,
registra `FAIL` o `NO EJECUTADO` con su código real y no marques su criterio.

## Evidencias del ejecutor

Completa sin pegar logs extensos:

| Directorio | Comando | Código | Resultado |
|---|---|---:|---|
| `/home/honor/.hermes/worktrees/local-ai-task-001-v3` | Unit tests | 0 | 10 tests OK |
| `/home/honor/.hermes/worktrees/local-ai-task-001-v3` | Ayuda CLI | 0 | CLI funcional |
| `/home/honor/.hermes/worktrees/local-ai-task-001-v3` | `git diff --check` | 0 | Sin errores |
| `/home/honor/.hermes/worktrees/local-ai-task-001-v3` | `git status --short` | 0 | Sólo rutas permitidas |

## Handoff

El candidato v3 fue aceptado tras auditoría independiente y dos correcciones
mecánicas del auditor. Consultar [`../audits/TASK-001-hermes-v3.md`](../audits/TASK-001-hermes-v3.md).
Los candidatos v1 y v2 permanecen conservados para comparación.
