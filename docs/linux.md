# Ejecutar desde GitHub en Linux

La distribución inicial soportada es un *checkout* o el ZIP de fuentes de
GitHub. No se considera soportada todavía la instalación global mediante
`pip install`, porque las suites y los manifiestos forman parte del repositorio.

## Plataformas objetivo

- Debian 12, Ubuntu 22.04 o Ubuntu 24.04 con Python 3.10 o posterior.
- CPU x86-64 mediante el backend nativo de `llama.cpp`.
- GPU NVIDIA mediante CUDA Toolkit y un controlador compatible.
- Vulkan queda disponible como backend experimental para AMD/Intel.

Las dos configuraciones Linux de referencia iniciales son:

| Equipo | Ruta estable | Capacidad que se pretende observar |
|---|---|---|
| Sobremesa con GeForce RTX 3060 de 12 GB | CUDA | VRAM completa, offload híbrido y spill hacia RAM con CUDA Unified Memory |
| Honor MagicBook 16 AMD con 16 GB de RAM | CPU y Vulkan/RADV | Rendimiento CPU, aceleración iGPU y presión sobre RAM compartida |

El equipo físico de referencia se ha identificado como Ryzen 5 4600H Renoir
con Radeon integrada, 16 GB de RAM y Ubuntu 22.04. CPU continúa siendo la ruta
estable; la Radeon integrada se mide como una segunda campaña Vulkan/UMA.

## Dependencias base

En Debian 12, Ubuntu 22.04 o Ubuntu 24.04:

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

El proyecto requiere Python 3.10 o posterior. El commit fijado de `llama.cpp`
requiere CMake 3.14 o posterior.

## Obtener el proyecto

Desde el repositorio publicado:

```bash
git clone https://github.com/CarlosCHD24/local-ai-hardware-bench.git
cd local-ai-hardware-bench
./bin/linux-smoke
```

También se puede descargar y descomprimir el archivo de fuentes de una release.
Los comandos deben ejecutarse desde su directorio raíz.

## Honor MagicBook 16 AMD con 16 GB

En este equipo se debe forzar CPU para que una instalación de Vulkan presente
en el sistema no altere la serie comparable.

La primera prueba debe usar sólo el modelo de 1.5B:

```bash
./bin/local-ai-bench doctor --backend cpu
./bin/local-ai-bench prepare --backend cpu --model qwen2.5-1.5b-instruct-q4_k_m
./bin/local-ai-bench run \
  --backend cpu \
  --system-id honor-magicbook16-amd-16gb \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

`prepare` clona el commit fijado de `llama.cpp`, compila `llama-bench`, descarga
el modelo y verifica su SHA-256. No necesita privilegios de administrador.

Después puede ejecutarse `quick-v1` completa. Sus modelos de 1.5B, 3B y 7B
deben caber con holgura en 16 GB y sirven como medida de rendimiento CPU:

```bash
./bin/local-ai-bench run --backend cpu \
  --system-id honor-magicbook16-amd-16gb
```

Para presión de memoria, `capacity-v1` selecciona automáticamente el perfil
`cpu-resident`. Conviene preparar y ejecutar primero 14B y sólo después 32B:

```bash
./bin/local-ai-bench --suite capacity-v1 prepare --backend cpu --yes \
  --model qwen2.5-14b-instruct-q4_k_m
./bin/local-ai-bench --suite capacity-v1 run --backend cpu \
  --system-id honor-magicbook16-amd-16gb \
  --model qwen2.5-14b-instruct-q4_k_m
```

El modelo 32B ocupa más que los 16 GB físicos. Su fallo, timeout, caída de RAM
disponible, aumento de page faults o uso de swap son resultados de capacidad
válidos. El proceso se detiene al alcanzar los límites de seguridad y nunca
consume más de cinco minutos de presupuesto por modelo.

## Radeon integrada: Vulkan/UMA experimental

Primero identifica el hardware y el controlador:

```bash
lscpu | grep "Model name"
lspci -nnk | grep -EA3 "VGA|Display"
```

En Ubuntu 24.04 o Debian instala la implementación Mesa/RADV y las herramientas
de compilación Vulkan desde los repositorios de la distribución:

```bash
sudo apt install -y mesa-vulkan-drivers vulkan-tools \
  libvulkan-dev glslc spirv-headers
vulkaninfo --summary
./bin/linux-smoke vulkan
```

Ubuntu 22.04 incluye Mesa/RADV pero no publica el paquete `glslc` requerido por
el commit fijado de `llama.cpp`. En Jammy se usa el repositorio oficial de
LunarG y su SDK Vulkan:

```bash
wget -qO- https://packages.lunarg.com/lunarg-signing-key-pub.asc | \
  sudo tee /etc/apt/trusted.gpg.d/lunarg.asc >/dev/null
sudo wget -qO /etc/apt/sources.list.d/lunarg-vulkan-jammy.list \
  http://packages.lunarg.com/vulkan/lunarg-vulkan-jammy.list
sudo apt update
sudo apt install -y cmake shaderc libvulkan-dev vulkan-headers \
  spirv-headers vulkan-tools
vulkaninfo --summary
./bin/linux-smoke vulkan
```

Los paquetes de LunarG aportan `glslc`, herramientas y cabeceras sin instalar
el metapaquete gráfico completo; el controlador físico continúa siendo
Mesa/RADV. No se instala ni se necesita ROCm para esta ruta.

El diagnóstico debe mostrar una Radeon física con topología `unified`. Rechaza
una instalación que sólo exponga `llvmpipe` o `lavapipe`, porque sería Vulkan
software ejecutándose sobre CPU.

Compila un runtime separado y empieza por 1.5B:

```bash
./bin/local-ai-bench prepare --backend vulkan \
  --model qwen2.5-1.5b-instruct-q4_k_m
./bin/local-ai-bench run --backend vulkan \
  --system-id honor-magicbook16-amd-16gb \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

Los builds CPU y Vulkan se guardan en directorios distintos. La detección
`auto` continúa eligiendo CPU en este portátil deliberadamente; Vulkan siempre
debe solicitarse con `--backend vulkan` para no mezclar campañas.

Si 1.5B termina y el resultado informa backend Vulkan y capas GPU, continúa con
3B y 7B. Para capacidad, prepara 14B antes de considerar 32B:

```bash
./bin/local-ai-bench --suite capacity-v1 prepare --backend vulkan --yes \
  --model qwen2.5-14b-instruct-q4_k_m
./bin/local-ai-bench --suite capacity-v1 run --backend vulkan \
  --system-id honor-magicbook16-amd-16gb \
  --model qwen2.5-14b-instruct-q4_k_m
```

En una APU no existe un depósito de VRAM independiente comparable con la RTX
3060. `VRAM` en `amdgpu` representa principalmente el carveout reservado y GTT
representa RAM del sistema accesible por la GPU. El informe etiqueta la
topología como `unified` y el modo como `shared_memory_pressure`, nunca como
spill de VRAM hacia RAM. Las cifras AMD son globales para el dispositivo, no
atribuibles exclusivamente al proceso.

## Sobremesa: GeForce RTX 3060 de 12 GB

El controlador y `nvidia-smi` no bastan para compilar. También debe estar
instalado CUDA Toolkit y `nvcc` debe encontrarse en `PATH`:

```bash
nvidia-smi
nvcc --version
./bin/linux-smoke auto
./bin/local-ai-bench doctor --backend cuda
```

`doctor` debe mostrar `Backend seleccionado: cuda`. Si muestra CPU, no se debe
publicar esa ejecución como resultado RTX 3060 hasta instalar o exponer el CUDA
Toolkit correctamente.

Después se utiliza el mismo flujo:

```bash
./bin/local-ai-bench prepare \
  --backend cuda \
  --model qwen2.5-1.5b-instruct-q4_k_m
./bin/local-ai-bench run \
  --backend cuda \
  --system-id desktop-rtx3060-12gb \
  --model qwen2.5-1.5b-instruct-q4_k_m
```

Tras verificar el modelo pequeño puede ejecutarse `quick-v1` completa; los tres
modelos están pensados para caber en los 12 GB de VRAM de esta tarjeta:

```bash
./bin/local-ai-bench run --backend cuda \
  --system-id desktop-rtx3060-12gb
```

Para explorar el límite de VRAM de forma progresiva:

```bash
./bin/local-ai-bench --suite capacity-v1 prepare --backend cuda --yes \
  --model qwen2.5-14b-instruct-q4_k_m
./bin/local-ai-bench --suite capacity-v1 run --backend cuda \
  --system-id desktop-rtx3060-12gb \
  --model qwen2.5-14b-instruct-q4_k_m
```

El perfil `auto-fit` reduce la memoria del dispositivo mediante colocación
híbrida. `full-accelerator` solicita todas las capas y, sólo con CUDA, activa
`GGML_CUDA_ENABLE_UNIFIED_MEMORY=1` para observar el desbordamiento hacia RAM.
Los informes separan RAM, swap y VRAM globales de las métricas atribuibles al
grupo de procesos cuando el driver las proporciona.

En la RTX 3060, 14B permite observar el borde de los 12 GB dependiendo del
contexto y los buffers. El modelo 32B fuerza una colocación híbrida o Unified
Memory y debe ejecutarse sólo después de validar 14B. Ambos conservan el límite
de cinco minutos por modelo.

## Vulkan genérico

En Debian o Ubuntu 24.04 suelen ser necesarios:

```bash
sudo apt install -y libvulkan-dev vulkan-tools glslc spirv-headers
./bin/local-ai-bench doctor --backend vulkan
```

Se ejecuta con `--backend vulkan`. En AMD/Linux se muestrean las métricas
globales de `amdgpu`; no hay atribución por proceso y la telemetría equivalente
para Intel queda pendiente.

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
- En el Honor MagicBook 16 usa explícitamente `--backend cpu`; Vulkan es una
  campaña distinta.
- Si Vulkan informa `llvmpipe` o `lavapipe`, instala o corrige Mesa/RADV; esa
  salida no representa la Radeon integrada.
- Si falla CMake, conserva su salida completa; el proyecto muestra el código de
  error pero el diagnóstico concreto procede de CMake o del compilador.
- Si el modelo no cabe, `capacity-v1` corta a los cinco minutos por modelo y
  también protege el sistema frente a swap o memoria disponible extremos.
