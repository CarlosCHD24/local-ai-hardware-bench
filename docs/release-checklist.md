# Checklist de release

## Calidad local

- [ ] `python3 -m unittest discover -s tests -v` termina sin fallos.
- [ ] `python3 -m compileall -q src tests` termina sin errores.
- [ ] `git diff --check` no encuentra problemas de formato.
- [ ] Las suites y manifiestos cargan mediante `doctor`.
- [ ] La versión coincide en `pyproject.toml` y `src/local_ai_bench/__init__.py`.
- [ ] `.local-ai-bench/` y los resultados privados no están preparados para commit.

## Checkout Linux CPU

- [ ] El checkout se ejecuta con Python 3.10 o posterior.
- [ ] `./bin/linux-smoke cpu` termina correctamente.
- [ ] `prepare --backend cpu --skip-models` compila el commit fijado.
- [ ] Qwen2.5 1.5B se descarga, verifica y ejecuta.
- [ ] El resultado generado pasa `validate`.

## Linux NVIDIA

- [ ] `nvidia-smi` y `nvcc --version` funcionan.
- [ ] `doctor --backend cuda` no muestra fallos.
- [ ] El runtime CUDA se compila desde cero.
- [ ] `quick-v1` con 1.5B termina y registra GPU, driver y VRAM.
- [ ] `capacity-v1 / auto-fit` registra capas reales y colocación híbrida o completa.
- [ ] `capacity-v1 / full-accelerator` registra que CUDA UM está activado.
- [ ] Se registran RAM, swap y VRAM del proceso cuando el driver lo permite.
- [ ] Ningún modelo excede el presupuesto total de cinco minutos.

## Linux AMD CPU

- [ ] `./bin/linux-smoke cpu` termina correctamente.
- [ ] `doctor --backend cpu` selecciona CPU aunque Vulkan esté instalado.
- [ ] `quick-v1` ejecuta 1.5B, 3B y 7B con cero capas de GPU.
- [ ] `capacity-v1` selecciona únicamente `cpu-resident`.
- [ ] El informe registra RAM disponible, RSS del proceso, swap y page faults.
- [ ] Ningún modelo excede el presupuesto total de cinco minutos.

## Linux AMD APU/Vulkan

- [ ] `lspci` identifica la Radeon integrada con el controlador `amdgpu`.
- [ ] `vulkaninfo --summary` muestra RADV y no `llvmpipe`/`lavapipe`.
- [ ] `./bin/linux-smoke vulkan` termina correctamente.
- [ ] El runtime Vulkan se compila separado del runtime CPU.
- [ ] GitHub Actions compila el runtime Vulkan fijado en Ubuntu 22.04 con el
  SDK oficial de LunarG.
- [ ] Qwen2.5 1.5B informa backend Vulkan, capas GPU y `uma: 1`.
- [ ] `capacity-v1` registra VRAM, GTT, actividad y RAM disponible.
- [ ] La colocación es `unified_gpu`/`unified_hybrid` y el spill mode es
  `shared_memory_pressure`.
- [ ] Se comparan CPU y Vulkan mostrando el backend en la cabecera.

## Privacidad y publicación

- [ ] Se revisan `system.json`, `manifest.json` y `raw/*.stderr.txt`.
- [ ] GitHub Actions termina correctamente en todas las versiones de Python.
- [ ] La rama principal está limpia y contiene únicamente archivos previstos.
- [ ] Se crea un tag anotado con la misma versión del proyecto.
- [ ] La release indica backends probados y limitaciones conocidas.
