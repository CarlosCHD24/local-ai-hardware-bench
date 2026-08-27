# Metodología de `quick-v1`

## Objetivo

Medir la capacidad práctica de un sistema para ejecutar inferencia LLM local.
No se pretende aislar el silicio del resto del equipo ni medir la calidad del
modelo. El sistema bajo prueba incluye hardware, sistema operativo, drivers,
compilador, configuración de `llama.cpp` y backend.

## Carga de trabajo

La suite utiliza modelos de una misma familia y cuantización para reducir
variables ajenas al hardware. `llama-bench` genera entradas sintéticas, por lo
que el idioma y el contenido de un prompt no afectan a la medición.

| Escenario | Significado | Métrica principal |
|---|---|---|
| `pp512` | Prefill de 512 tokens | tokens/s |
| `pp4096` | Prefill de 4096 tokens | tokens/s |
| `tg128` | Decode de 128 tokens | tokens/s |

Antes de cada medición se hace una ejecución de calentamiento que se descarta.
Después se realizan cinco repeticiones. Se conservan las muestras individuales,
la media y la desviación estándar reportadas por `llama-bench`.

Cuando existe `/usr/bin/time`, se registra también el pico RSS del proceso. En
CUDA este dato describe la RAM del proceso y no la VRAM de la GPU. En Apple
Silicon la memoria es unificada, pero RSS sigue sin representar por sí solo toda
la presión de memoria del sistema; por eso se publica como métrica secundaria.

`llama-bench` no incluye tokenización ni sampling en sus tiempos. Esto es
deliberado: `quick-v1` es un microbenchmark del runtime y del hardware, no una
prueba de experiencia completa de una aplicación.

## Reglas de ejecución

1. Usar la suite sin modificar.
2. Mantener los SHA-256 de todos los modelos.
3. Usar la revisión de `llama.cpp` indicada por la suite.
4. Conectar portátiles a corriente y registrar el gobernador cuando sea visible.
5. Cerrar cargas intensivas antes de empezar.
6. No seleccionar ni publicar únicamente la mejor repetición.
7. No ocultar fallos, timeouts u OOM.
8. Indicar cualquier argumento manual, como `--threads` o `--backend`.
9. Comparar únicamente ejecuciones del mismo ID de suite.
10. Conservar los archivos brutos para permitir auditoría.

## Backends

- Metal: backend normal en Apple Silicon.
- CUDA: backend normal para NVIDIA cuando está instalado el CUDA Toolkit.
- CPU: referencia portátil y opción inicial para equipos Linux sin acelerador
  compatible.
- Vulkan: opción experimental; debe indicarse explícitamente y sus resultados
  no deben mezclarse con CPU sin mostrar el backend. En una APU con `uma: 1`,
  sus asignaciones consumen la misma RAM física que utiliza la CPU.

La suite solicita descargar hasta 99 capas en el acelerador. El resultado de
`llama-bench` registra cuántas capas se utilizaron realmente. En CPU se fuerza
cero capas GPU.

## Qué no mide esta versión

- Calidad, razonamiento o precisión del modelo.
- Latencia end-to-end de una API.
- Concurrencia multiusuario.
- Tiempo de descarga.
- Un arranque genuinamente en frío.
- Energía comparable entre plataformas.
- Throttling en cargas prolongadas.

Estas dimensiones pueden incorporarse mediante nuevas suites sin cambiar el
significado de `quick-v1`.

## Versionado

Una suite publicada es inmutable. Cambiar modelos, hashes, escenarios,
repeticiones, runtime o parámetros crea un nuevo ID (`quick-v2`, por ejemplo).
Corregir un parser sin alterar la ejecución puede hacerse en el código, siempre
que la salida bruta permita regenerar los resultados.
