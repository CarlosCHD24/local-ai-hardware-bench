# Metodología de `capacity-v1`

## Objetivo

Encontrar el límite práctico de memoria del sistema y cuantificar qué ocurre
cuando el modelo deja de residir cómodamente en la memoria rápida. La suite no
sustituye a `quick-v1` ni mezcla sus resultados con ella.

## Cargas

La primera versión fija Qwen2.5 Instruct 14B y 32B en `Q4_K_M`, tres
repeticiones y dos escenarios breves: `tg32` y `pp512`. Los artefactos,
revisiones y SHA-256 están fijados en el manifiesto.

El perfil `auto-fit` utiliza `--fit-target 1024 --fit-ctx 4096`; no fija
`n_gpu_layers`, de modo que `llama.cpp` puede ajustar la colocación. El perfil
`full-accelerator` solicita 99 capas. Ambos fijan el modo de carga `mmap`.

## Telemetría

El muestreo comienza antes de lanzar la carga y termina después de que sale el
proceso. Se conserva la serie temporal completa y un resumen normalizado.

- macOS: memoria disponible, swap, compresor, page-ins/page-outs y
  swap-ins/swap-outs.
- Linux: `MemAvailable`, swap y contadores de `/proc/vmstat`.
- NVIDIA: además se consulta VRAM usada y total mediante `nvidia-smi`.
- Linux atribuye al grupo de procesos su pico de RSS, swap y, cuando el driver
  lo informa, memoria CUDA. La VRAM global se conserva por separado.
- Todas las plataformas: pico RSS mediante `/usr/bin/time` y buffers/capas
  reportados por la salida verbose de `llama.cpp`.

El muestreador observa contadores del sistema. Por tanto, swap, compresión y
fallos de página pueden incluir actividad externa; hay que cerrar cargas
intensivas antes de ejecutar.

En CUDA, `auto-fit` mide colocación híbrida sin forzar el desbordamiento. El
perfil `full-accelerator` activa `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`, solicita
todas las capas y permite observar la caída de RAM disponible y la memoria de
proceso cuando la VRAM se llena. Esta variable no se aplica a CPU, Metal ni
Vulkan.

CUDA y `nvidia-smi` no ofrecen en esta ruta una cifra directa y portable de
“bytes migrados a RAM”. El informe conserva por ello evidencias separadas
(VRAM del proceso, RSS, swap del proceso y caída de RAM disponible) y marca si
CUDA UM estaba activado, sin presentar una estimación indirecta como medida
exacta de *spill*.

## Clasificación

`placement` describe dónde se ejecutó el modelo. `pressure` describe el efecto
sobre el sistema. Un crecimiento de swap de al menos 64 MiB o cualquier
swap-out clasifica la prueba como `swapping`; un crecimiento de compresión de
al menos 256 MiB sin swap se clasifica como `compressed`.
Si ya existían al menos 64 MiB de swap al comenzar pero no aumentan durante la
prueba, se utiliza `swap_resident`. El informe muestra siempre swap inicial,
pico y crecimiento porque macOS puede conservar páginas intercambiadas entre
procesos consecutivos.

La seguridad forma parte del protocolo: una prueba se marca
`aborted_pressure` cuando supera 8 GiB de crecimiento de swap o cae por debajo
del 3 % de memoria disponible. Si el runtime o el sistema rechazan la
asignación, el estado es `oom`. Un `timeout`, un `oom` o un
`aborted_pressure` omiten todos los perfiles y escenarios restantes del mismo
modelo para no repetir una carga que ya alcanzó el límite de capacidad.

Cada modelo dispone además de un presupuesto total estricto de 300 segundos,
compartido por todos sus perfiles y escenarios. Si se agota, la operación en
curso se marca `timeout` y el resto se registra como `skipped`; no se reinicia
otro perfil que repetiría el mismo *thrashing*. Este límite forma parte de la
definición de `capacity-v1`, por lo que no debe ampliarse al comparar equipos.

## Comparabilidad

Solo deben compararse ejecuciones completas de `capacity-v1` con la misma
revisión de runtime y los mismos artefactos. Las selecciones parciales son
útiles para diagnóstico, pero deben publicarse identificando claramente los
modelos y perfiles ejecutados.
