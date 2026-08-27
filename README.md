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

Los resultados publicados forman un historial acumulativo. Las cifras de una
misma tabla comparten suite, modelos, cuantización y revisión de `llama.cpp`;
el backend se muestra siempre para evitar comparar CPU, Metal, Vulkan y CUDA
como si fueran la misma configuración.

### Equipos probados

| ID público | Hardware | Memoria | Sistema | Estado |
|---|---|---:|---|---|
| `macbook-m4` / `macbook-m4-16gb` | Apple M4, GPU integrada de 10 núcleos | 16 GiB unificados | macOS 26.1 | `quick-v1` y `capacity-v1` |
| `honor-magicbook16-amd-16gb` | Ryzen 5 4600H, Radeon Renoir integrada | 15 GiB utilizables | Ubuntu 22.04.5 | `quick-v1` Vulkan, modelo 1.5B |
| `desktop-ryzen7-5800x-32gb` | Ryzen 7 5800X, GeForce RTX 3060 12 GB | 31.3 GiB + 12 GB VRAM | Ubuntu 24.04.4 | `quick-v1` CPU, modelo 1.5B |

El procesador del Honor se documenta como Ryzen 5 4600H porque es el modelo
detectado por el propio sistema durante la prueba.

### Historial `quick-v1`

Rendimiento en tokens/s; un valor mayor es mejor. `pp` mide procesamiento de
prompt y `tg` generación. Cada enlace abre el informe completo de esa ejecución.

| Fecha UTC | Equipo | Backend | Modelo Q4_K_M | pp512 | pp4096 | tg128 | Informe |
|---|---|---|---|---:|---:|---:|---|
| 2026-08-26 | MacBook M4 | Metal | Qwen2.5 1.5B | 1164.78 | 1022.37 | 88.94 | [ver](results/quick-v1/macbook-m4/20260826T140126Z/report.md) |
| 2026-08-26 | MacBook M4 | Metal | Qwen2.5 3B | 524.11 | 478.25 | 47.55 | [ver](results/quick-v1/macbook-m4/20260826T140126Z/report.md) |
| 2026-08-26 | MacBook M4 | Metal | Qwen2.5 7B | 231.70 | 219.19 | 22.04 | [ver](results/quick-v1/macbook-m4/20260826T140126Z/report.md) |
| 2026-08-27 | Honor MagicBook 16 | Vulkan | Qwen2.5 1.5B | 248.20 | 172.46 | 26.30 | [ver](results/quick-v1/honor-magicbook16-amd-16gb/20260827T091750Z/report.md) |
| 2026-08-27 | Sobremesa Ryzen 7 5800X | CPU | Qwen2.5 1.5B | 274.35 | 226.61 | 29.09 | [ver](results/quick-v1/desktop-ryzen7-5800x-32gb/20260827T141123Z/report.md) |

La RTX 3060 aparece en el inventario del sobremesa, pero no intervino en la
última fila: el backend fue CPU y se registraron cero capas GPU. La campaña
CUDA queda pendiente de instalar CUDA Toolkit/`nvcc`; hasta entonces no se
publicará ningún resultado como rendimiento de la RTX 3060.

### Historial `capacity-v1`

| Fecha UTC | Equipo | Backend | Modelo / perfil | Resultado | Presión de memoria | Informe |
|---|---|---|---|---|---|---|
| 2026-08-26 | MacBook M4 16 GB | Metal | Qwen2.5 14B / `auto-fit` | tg32 11.35; pp512 120.38 tokens/s | Swap creció 2.3 GiB al inicio | [ver](results/capacity-v1/macbook-m4-16gb/20260826T150846Z/report.md) |
| 2026-08-26 | MacBook M4 16 GB | Metal | Qwen2.5 14B / `full-accelerator` | tg32 11.54; pp512 117.85 tokens/s | Memoria comprimida, sin nuevo swap significativo | [ver](results/capacity-v1/macbook-m4-16gb/20260826T150846Z/report.md) |
| 2026-08-26 | MacBook M4 16 GB | Metal | Qwen2.5 32B / `auto-fit` | Abortado por presión; pp512 omitido | Swap creció 8.6 GiB | [ver](results/capacity-v1/macbook-m4-16gb/20260826T153659Z/report.md) |

Cada ejecución local genera:

```text
results/quick-v1/<system-id>/<UTC-run-id>/
├── manifest.json
├── system.json
├── raw/
├── results.json
├── results.csv
└── report.md
```

Los resultados se ignoran por defecto. Para el historial se publican
`manifest.json`, `system.json`, `results.json`, `results.csv` y `report.md`
después de validar y revisar su privacidad. `raw/` permanece local porque puede
contener rutas del equipo y una gran cantidad de telemetría; no es necesario
para consultar las cifras normalizadas.

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
