# Pruebas pendientes en el sobremesa (RTX 3060) — desktop-ai

Fecha: 2026-10-03 · Rama: `hermes/preflight-hardening` · Suite dev: 73 passed + 15 subtests (verde, sin GPU).

Todo lo siguiente NO ha podido ejecutarse en el equipo de desarrollo (sin
GPU ni ruta a la red del homelab). Son las pruebas que faltan para cerrar el
monitoring. Copia esta rama al sobremesa y sigue el orden.

## 0. Preparación en desktop-ai

```bash
cd ~/local-ai-hardware-bench       # o donde tengas el repo
git fetch origin
git checkout hermes/preflight-hardening
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml
cd monitoring && ls  # confirmar artefactos
```

## 1. Tests completos con GPU presente

```bash
cd ~/local-ai-hardware-bench
.venv/bin/python -m pytest monitoring/tests monitoring/contract_tests -q --no-header -o 'testpaths='
```
Esperado: **73 passed, 15 subtests passed** (mismos números que en dev).

## 2. Preflight perfil server (obligatorio: exit 0 en produccion)

```bash
.venv/bin/python monitoring/preflight.py --profile server --json
```
Comprobaciones y causas de fallo tipicas:
- `systemctl` → debe estar (siempre).
- `nvidia-smi` → aquí es OBLIGATORIO (en dev era solo warning). Debe responder
  con la RTX 3060. Si `which nvidia-smi` existe pero el driver falla, el check
  actual solo verifica presencia del binario — informalo si detectas ese caso
  (candidato a endurecer: ejecutar `nvidia-smi --query-gpu=name` real).
- `validate_prometheus` / `validate_operation` → exit 0.
- `promtool check config monitoring/prometheus/prometheus.yml` → en server es
  obligatorio: instala `prometheus` (aporta promtool) o dime el fallo.
- `systemd-analyze verify monitoring/systemd/*` → sin errores de sintaxis de
  unidades.

## 3. Colector NVIDIA real (TASK-005/007)

```bash
# salida en formato textfile hacia un dir temporal (la opcion es --directory, obligatoria)
mkdir -p /tmp/tf-check
.venv/bin/python -m monitoring.nvidia_textfile --directory /tmp/tf-check --timeout 5
.venv/bin/python monitoring/nvidia_metrics.py   # muestra Prometheus por stdout (--timeout 5)
```
Esperado: lectura correcta de utilization, mem, temperatura, potencia de la
RTX 3060. Guarda una salida de muestra.

## 4. Despliegue systemd del colector (TASK-015/016/010)

```bash
# sigue los pasos de monitoring/deployment.md seccion correspondiente
sudo cp monitoring/systemd/local-ai-nvidia-metrics.{service,timer} /etc/systemd/system/
sudo cp monitoring/systemd/node-exporter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now local-ai-nvidia-metrics.timer node-exporter
systemctl list-timers | grep nvidia
```

## 5. Frescura del textfile (check_nvidia_textfile, base de TASK-020)

```bash
.venv/bin/python monitoring/check_nvidia_textfile.py \
  --directory /var/lib/node_exporter/textfile_collector --max-age 45
```
Esperado: exit 0 con `[OK] frescura: ... <= 45s`, `[OK] scrape_success 1`,
`[OK] metricas GPU: 5/5`. La ruta real del textfile puede diferir — mira
`--web.textfile-collector` en node-exporter.service y usa esa.
Prueba negativa: `sudo systemctl stop local-ai-nvidia-metrics.timer`, espera
>45 s, repite → debe dar exit 1 por frescura.

## 6. Listeners en loopback (check_listeners)

```bash
.venv/bin/python monitoring/check_listeners.py --require 127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000
```
Esperado exit 0 con Prometheus (arrancado con `--web.listen-address=127.0.0.1:9090`),
Grafana (`http_addr=127.0.0.1`) y node_exporter operativos.
Preflight integrado:
```bash
.venv/bin/python monitoring/preflight.py --profile server \
  --require-listeners 127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000 \
  --textfile-dir /var/lib/node_exporter/textfile_collector
```

## 7. Preflight servidor integrado (prueba maestra)

```bash
.venv/bin/python monitoring/preflight.py --profile server --json \
  --require-listeners 127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000 \
  --textfile-dir /var/lib/node_exporter/textfile_collector
```
Esperado: `exit_code: 0`, todos los checks `ok`. Pega la salida JSON completa
en la prueba.

## 8. Hueco conocido: retencion 30 dias (TASK-019)

Los artefactos NO fijan aun `--storage.tsdb.retention.time=30d`. Al desplegar
Prometheus usalo explicitamente y confirma que se acepta. Queda pendiente
versionarlo en las unidades/flags cuando confirmes la ruta de arranque real.

## Resultado esperado a reportar

Para cada punto 1-7: comando, exit code, y salida relevante (capturas o texto).
Cualquier divergencia respecto a "esperado" es un hallazgo: anotarlo en este
mismo fichero y lo convertimos en tarea/fix.
