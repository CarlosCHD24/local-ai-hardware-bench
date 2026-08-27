# Local AI Hardware Bench

Suite pequeña, reproducible y extensible para medir la capacidad práctica de un
equipo ejecutando modelos de IA en local. La versión 1 compara inferencia LLM
con el mismo `llama.cpp`, los mismos modelos GGUF y los mismos escenarios.

No evalúa la calidad de las respuestas. Los modelos son cargas de trabajo fijas
para medir procesamiento de prompt y generación en tokens por segundo.

## Alcance de `quick-v1`

- Qwen2.5 Instruct 1.5B, 3B y 7B.
- Cuantización común `Q4_K_M`.
- `llama.cpp` fijado a un commit concreto.
- Linux CPU, Linux CUDA y macOS Apple Silicon/Metal.
- Vulkan disponible para GPU integrada AMD como opción experimental UMA.
- Escenarios `pp512`, `pp4096` y `tg128`.
- Una ejecución de calentamiento y cinco repeticiones medidas.
- Pico de memoria residente del proceso cuando `/usr/bin/time` lo permite.
- Salida bruta, JSON normalizado, CSV e informe Markdown.

La descarga completa de modelos ocupa aproximadamente 7.4 GiB.

## Alcance de `capacity-v1`

`capacity-v1` complementa el microbenchmark rápido y explora el límite de
memoria con Qwen2.5 14B y 32B `Q4_K_M` (aproximadamente 26.9 GiB en total).
Ejecuta perfiles compatibles con el backend seleccionado:

- `cpu-resident`: carga mediante `mmap` y fuerza CPU sin offload.
- `auto-fit`: deja que `llama.cpp` ajuste la colocación conservando 1 GiB de
  margen en el dispositivo.
- `full-accelerator`: solicita todas las capas y conserva OOM o aborto por
  presión como resultados válidos.

En CPU sólo se ejecuta `cpu-resident`; CUDA, Metal y Vulkan usan `auto-fit` y
`full-accelerator`. Así no se aplican opciones de ajuste de VRAM a equipos que
carecen de una GPU compatible.

Cada proceso se muestrea una vez por segundo. Se registran swap, compresión,
memoria disponible, page-ins/page-outs, colocación real de capas y buffers y,
cuando existe, memoria del dispositivo. En Linux AMD también se registran VRAM
reservada, GTT y actividad global de `amdgpu`. La suite aborta una prueba si el
swap crece más de 8 GiB o la memoria disponible cae por debajo del 3 %.

## Requisitos

- Python 3.10 o posterior.
- Git, CMake y un compilador C/C++.
- macOS: Xcode Command Line Tools.
- NVIDIA: controlador compatible y CUDA Toolkit con `nvcc` para compilar el
  backend CUDA.
- AMD APU: Mesa/RADV, Vulkan loader, `vulkaninfo`, `glslc` y cabeceras SPIR-V.
  Ubuntu 22.04 obtiene las herramientas de compilación mediante el SDK oficial
  de LunarG; Ubuntu 24.04 puede usar sus paquetes estándar.
- Espacio adicional para compilar `llama.cpp` y descargar los modelos.

Las instrucciones completas por backend y distribución están en
[`docs/linux.md`](docs/linux.md). La primera distribución soportada desde
GitHub es el checkout o ZIP de fuentes; la instalación global con `pip` queda
fuera del alcance de esta versión.

No hay dependencias Python obligatorias. Se puede ejecutar directamente desde
el checkout:

```bash
./bin/local-ai-bench --help
```

También puede instalarse en editable:

```bash
python3 -m pip install -e .
local-ai-bench --help
```

## Uso rápido

### 1. Revisar el equipo

```bash
./bin/local-ai-bench doctor
```

La detección automática elige Metal en Apple Silicon, CUDA en Linux cuando
encuentra `nvcc` y `nvidia-smi`, y CPU en el resto. Se puede forzar la decisión:

```bash
./bin/local-ai-bench doctor --backend cpu
./bin/local-ai-bench doctor --backend cuda
./bin/local-ai-bench doctor --backend vulkan
```

En Linux se puede ejecutar primero el smoke test sin descargar modelos:

```bash
./bin/linux-smoke
```

Sin argumento, el smoke test usa detección automática: CUDA cuando están
disponibles `nvidia-smi` y `nvcc`, CPU en el resto.

### 2. Preparar runtime y modelos

```bash
./bin/local-ai-bench prepare
```

El comando solicita confirmación antes de descargar. Para entornos no
interactivos:

```bash
./bin/local-ai-bench prepare --yes
```

Para preparar solo un modelo:

```bash
./bin/local-ai-bench prepare \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

Para preparar la suite de capacidad de forma progresiva:

```bash
./bin/local-ai-bench --suite capacity-v1 prepare --yes \
  --model qwen2.5-14b-instruct-q4_k_m
./bin/local-ai-bench --suite capacity-v1 prepare --yes \
  --model qwen2.5-32b-instruct-q4_k_m
```

Los datos se guardan en `.local-ai-bench/`, que está excluido de Git. Puede
cambiarse con `--home /ruta` o `LOCAL_AI_BENCH_HOME`.

### 3. Ejecutar

El identificador del sistema debe ser público y no contener hostname, nombre de
usuario ni número de serie:

```bash
./bin/local-ai-bench run --system-id desktop-rtx3060-12gb --backend cuda
./bin/local-ai-bench run --system-id macbook-m4-16gb
./bin/local-ai-bench run --system-id honor-magicbook16-amd-16gb --backend cpu
./bin/local-ai-bench run --system-id honor-magicbook16-amd-16gb --backend vulkan
```

Para una primera comprobación se puede ejecutar únicamente el modelo pequeño:

```bash
./bin/local-ai-bench run \
  --system-id equipo-prueba \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

La suite de capacidad permite seleccionar modelo y perfil:

```bash
./bin/local-ai-bench --suite capacity-v1 run \
  --system-id macbook-m4-16gb \
  --model qwen2.5-14b-instruct-q4_k_m \
  --profile auto-fit
```

Tanto `quick-v1` como `capacity-v1` aplican un presupuesto total máximo de 5
minutos por modelo, compartido entre sus perfiles y escenarios. Si se alcanza
un `timeout`, un `oom` o el corte por presión de memoria, registra el resultado
y omite las cargas restantes de ese modelo.

### 4. Comparar

```bash
./bin/local-ai-bench compare \
  results/quick-v1/honor-magicbook16-amd-16gb/EJECUCION-CPU \
  results/quick-v1/honor-magicbook16-amd-16gb/EJECUCION-VULKAN \
  --output comparison.md
```

La comparación incluye el backend en cada cabecera, por lo que dos ejecuciones
del mismo equipo se distinguen como `[cpu]` y `[vulkan]`.

## Resultados

Cada ejecución genera:

```text
results/quick-v1/<system-id>/<UTC-run-id>/
├── manifest.json
├── system.json
├── raw/
├── results.json
├── results.csv
└── report.md
```

Los resultados se ignoran por defecto. Antes de publicarlos, hay que añadirlos
explícitamente a Git y revisar `system.json`.

## Comandos

| Comando | Función |
|---|---|
| `doctor` | Detecta plataforma, herramientas y backend |
| `prepare` | Compila `llama.cpp`, descarga y verifica modelos |
| `run` | Ejecuta la suite y conserva todos los resultados |
| `validate` | Comprueba la consistencia de una ejecución |
| `report` | Regenera Markdown y CSV desde el JSON normalizado |
| `compare` | Compara ejecuciones de la misma suite |

## Interpretación

- `pp512` y `pp4096` miden procesamiento del prompt o *prefill*.
- `tg128` mide generación o *decode*.
- Una cifra mayor en tokens/s indica más rendimiento para ese escenario.
- Un fallo u OOM es un resultado válido sobre la capacidad del sistema.
- No deben compararse suites con identificadores diferentes.
- La medición representa el sistema completo: hardware, SO, drivers,
  compilador, backend y runtime.

Consulta [la metodología](docs/methodology.md) antes de publicar comparaciones.
La interpretación específica de presión de memoria se describe en
[`docs/capacity-methodology.md`](docs/capacity-methodology.md).

## Desarrollo

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m local_ai_bench --suite quick-v1 doctor --backend cpu --json
```

El proyecto utiliza únicamente la biblioteca estándar en tiempo de ejecución.
Los esquemas JSON están en `schemas/` y GitHub Actions comprueba configuración,
parsers, informes y validación.

## Licencias

El código se publica bajo MIT. Los modelos Qwen2.5 utilizados por la suite se
referencian bajo Apache-2.0 y no se redistribuyen desde este repositorio.
`llama.cpp` se descarga desde su repositorio oficial y conserva su propia
licencia.
