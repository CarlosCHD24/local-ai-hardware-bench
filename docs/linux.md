# Ejecutar desde GitHub en Linux

La distribución inicial soportada es un *checkout* o el ZIP de fuentes de
GitHub. No se considera soportada todavía la instalación global mediante
`pip install`, porque las suites y los manifiestos forman parte del repositorio.

## Plataformas objetivo

- Debian 12 o Ubuntu 24.04 con Python 3.11 o posterior.
- CPU x86-64 mediante el backend nativo de `llama.cpp`.
- GPU NVIDIA mediante CUDA Toolkit y un controlador compatible.
- Vulkan queda disponible como backend experimental para AMD/Intel.

## Dependencias base

En Debian 12 o Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y python3 git cmake build-essential pciutils
```

Comprueba que las versiones mínimas están disponibles:

```bash
python3 --version
cmake --version
c++ --version
```

El proyecto requiere Python 3.11 o posterior. El commit fijado de `llama.cpp`
requiere CMake 3.14 o posterior.

## Obtener el proyecto

Cuando el repositorio esté publicado:

```bash
git clone https://github.com/CarlosCHD24/local-ai-hardware-bench.git
cd local-ai-hardware-bench
./bin/linux-smoke cpu
```

También se puede descargar y descomprimir el archivo de fuentes de una release.
Los comandos deben ejecutarse desde su directorio raíz.

## CPU

La primera prueba debe usar sólo el modelo de 1.5B:

```bash
./bin/local-ai-bench doctor --backend cpu
./bin/local-ai-bench prepare --backend cpu --model qwen2.5-1.5b-instruct-q4_k_m
./bin/local-ai-bench run \
  --backend cpu \
  --system-id ryzen-5400h-linux \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

`prepare` clona el commit fijado de `llama.cpp`, compila `llama-bench`, descarga
el modelo y verifica su SHA-256. No necesita privilegios de administrador.

## NVIDIA CUDA

El controlador y `nvidia-smi` no bastan para compilar. También debe estar
instalado CUDA Toolkit y `nvcc` debe encontrarse en `PATH`:

```bash
nvidia-smi
nvcc --version
./bin/local-ai-bench doctor --backend cuda
```

Después se utiliza el mismo flujo:

```bash
./bin/local-ai-bench prepare \
  --backend cuda \
  --model qwen2.5-1.5b-instruct-q4_k_m
./bin/local-ai-bench run \
  --backend cuda \
  --system-id desktop-nvidia-linux \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

Para explorar el límite de VRAM de forma progresiva:

```bash
./bin/local-ai-bench --suite capacity-v1 prepare --backend cuda --yes \
  --model qwen2.5-14b-instruct-q4_k_m
./bin/local-ai-bench --suite capacity-v1 run --backend cuda \
  --system-id desktop-nvidia-linux \
  --model qwen2.5-14b-instruct-q4_k_m
```

El perfil `auto-fit` reduce la memoria del dispositivo mediante colocación
híbrida. `full-accelerator` solicita todas las capas y, sólo con CUDA, activa
`GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` para observar el desbordamiento hacia RAM.
Los informes separan RAM, swap y VRAM globales de las métricas atribuibles al
grupo de procesos cuando el driver las proporciona.

## Vulkan experimental

En Debian/Ubuntu suelen ser necesarios:

```bash
sudo apt install -y libvulkan-dev vulkan-tools glslc
./bin/local-ai-bench doctor --backend vulkan
```

Se ejecuta con `--backend vulkan`. Esta ruta no ofrece todavía atribución de
VRAM para AMD/Intel y no forma parte de la matriz estable de `quick-v1`.

## Datos y resultados

Por defecto, runtimes y modelos se guardan en `.local-ai-bench/`. Para utilizar
otro disco:

```bash
export LOCAL_AI_BENCH_HOME=/ruta/con/espacio/local-ai-bench
```

Los resultados se crean bajo `results/<suite>/<system-id>/<run-id>/`. Antes de
publicarlos:

```bash
./bin/local-ai-bench validate results/SUITE/SISTEMA/EJECUCION
```

Revisa siempre `system.json` y los archivos `raw/*.stderr.txt` por privacidad.

## Diagnóstico

- Si `auto` selecciona CPU en un equipo NVIDIA, comprueba `nvcc --version` y
  `nvidia-smi`.
- Si falla CMake, conserva su salida completa; el proyecto muestra el código de
  error pero el diagnóstico concreto procede de CMake o del compilador.
- Si el modelo no cabe, `capacity-v1` corta a los cinco minutos por modelo y
  también protege el sistema frente a swap o memoria disponible extremos.
