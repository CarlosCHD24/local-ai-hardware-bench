# Interpretación de resultados

## Prefill y decode

El procesamiento del prompt y la generación tienen perfiles de hardware
distintos. Por ello no se promedian en una única puntuación:

- Prefill suele aprovechar más paralelismo de cálculo.
- Decode suele estar más condicionado por el ancho de banda de memoria.
- El tamaño del modelo muestra cómo escala el equipo al aumentar pesos y memoria.

Un equipo puede ser el más rápido en `pp4096` y no serlo en `tg128`. Ambos datos
son correctos y describen usos diferentes.

## Variabilidad

Una desviación alta puede indicar actividad en segundo plano, temperatura,
cambios de frecuencia o una configuración inestable. Conviene repetir la suite
completa, no una única fila, si la variación parece anormal.

## Offload

`n_gpu_layers` permite comprobar si el modelo se ejecutó en el acelerador. Un
resultado con offload parcial es útil, pero debe compararse mostrando esa
condición. En Apple Silicon la memoria es unificada; VRAM y RAM no son depósitos
independientes como en una GPU discreta.

## Fallos

`failed`, `timeout`, `oom` y `aborted_pressure` no se convierten en cero
tokens/s. Son estados distintos que indican que esa combinación no pudo
completarse bajo el protocolo.

## Colocación y presión

`capacity-v1` separa dos dimensiones que no deben confundirse:

- `placement`: `gpu_full`, `unified_gpu`, `unified_hybrid`, `hybrid`, `cpu` o
  `unknown`.
- `pressure`: `normal`, `compressed`, `swapping`, `swap_resident`, `oom` o
  `aborted`.

En una GPU discreta, `hybrid` significa que una parte del modelo quedó en RAM.
En Apple Silicon, `unified_gpu` indica que todas las capas se ejecutaron con
Metal, pero RAM y GPU siguen compartiendo la misma memoria física. El
incremento de swap y compresión se calcula respecto a la línea base de cada
proceso y no debe interpretarse como memoria exclusiva del benchmark si había
otras cargas activas.

La misma interpretación unificada se aplica a una APU AMD cuando `llama.cpp`
informa `uma: 1`. `unified_hybrid` indica offload parcial dentro de esa memoria
compartida. `amdgpu_vram_*`, `amdgpu_gtt_*` y actividad GPU son contadores
globales del dispositivo; sirven como evidencia de uso, no como atribución
exacta al proceso.
