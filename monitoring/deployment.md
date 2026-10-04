# Despliegue local de monitoring

Documento operativo del stack desplegado. Refleja los artefactos versionados y
las unidades systemd reales de `monitoring/`. No contiene claves ni
contraseñas: la credencial de `llama-server` vive fuera de Git.

## 1. Artefactos, copia y usuarios

- Copiar las unidades de `monitoring/systemd/` al directorio de unidades del
  sistema y validarlas con `systemd-analyze verify` antes de habilitarlas.
- `node-exporter.service` ejecuta
  `/usr/bin/prometheus-node-exporter --web.listen-address=127.0.0.1:9100
  --collector.textfile.directory=/var/lib/node_exporter/textfile_collector`
  como `User=prometheus`.
- `local-ai-nvidia-metrics.service` ejecuta el colector NVIDIA como
  `User=carlos`, `Group=prometheus` y
  `WorkingDirectory=/home/carlos/local-ai-hardware-bench`:
  `/usr/bin/python3 -m monitoring.nvidia_textfile --directory
  /var/lib/node_exporter/textfile_collector --timeout 5`.
- `local-ai-nvidia-metrics.timer` dispara la muestra cada 15 s
  (`OnBootSec=15s`, `OnUnitActiveSec=15s`, `RandomizedDelaySec=0`,
  `Persistent=true`).
- Crear `/var/lib/node_exporter/textfile_collector` con propietario
  `prometheus` (usuario de node_exporter) y escritura para el grupo
  `prometheus`, de forma que el colector (`carlos`) pueda dejar allí su
  `*.prom`.
- La clave de `llama-server` se mantiene fuera de Git en
  `/etc/local-ai-monitoring/llama-api-key` con permisos `0600`.
  Prometheus la lee mediante `bearer_token_file`; nunca se copia a la
  documentación.

## 2. Listeners locales

El stack sólo debe escuchar en loopback. Estado real de los artefactos:

| Componente | Listener | Origen versionado |
|---|---|---|
| node_exporter | `127.0.0.1:9100` | `systemd/node-exporter.service` y target de `prometheus/prometheus.yml` |
| Prometheus | `127.0.0.1:9090` | URL de `grafana/provisioning/datasources/prometheus.yml`; requiere arrancar Prometheus con `--web.listen-address=127.0.0.1:9090` |
| Grafana | `127.0.0.1:3000` | puerto por defecto de Grafana; requiere fijar `http_addr=127.0.0.1` y `http_port=3000` |

No existe en el repositorio una unidad systemd de Prometheus ni de Grafana: sus
listeners `9090` y `3000` son **requisitos de despliegue** que el operador debe
fijar en loopback, no hechos ya codificados. `validate_prometheus.py` y
`prometheus/prometheus.yml` sí versionan `127.0.0.1:9100` para node_exporter.

Prometheus scrapea:

- `local-ai-server` en `192.168.3.42:8080` con `bearer_token_file`;
- `node-exporter` en `127.0.0.1:9100`.

No se debe abrir ningún puerto de monitoring a Internet.

## 3. Retención

El objetivo es conservar **30 días** de datos. No hay ningún
`--storage.tsdb.retention.time` ni equivalente codificado en los artefactos; es
un requisito de despliegue pendiente de fijar al arrancar Prometheus
(`--storage.tsdb.retention.time=30d`) y de dimensionar en disco. `README.md`
(secciones 4.1 y 13) mantiene la retención definitiva como decisión abierta
hasta medir el volumen real de series.

## 4. Acceso por túnel SSH

Grafana escucha sólo en loopback del servidor. El acceso desde otro equipo de
la red doméstica se hace con un túnel SSH que reenvía el puerto local:

```bash
ssh -N -L 3000:127.0.0.1:3000 carlos@192.168.3.42
```

Después se abre `http://127.0.0.1:3000` en el equipo cliente. El túnel no
transporta claves por la línea de comandos y no publica el puerto en la LAN.

La IP `192.168.3.42` es la dirección inventariada del sobremesa `desktop-ai`
(servidor de inferencia) en la red doméstica. Es una dirección asignada por el
DHCP del router y conviene reservarla; si cambia, debe actualizarse el target
de `prometheus/prometheus.yml`. No se debe hardcodear como dirección fija
inmutable.

## 5. Validación con preflight

Desde la raíz del repositorio, con `.venv` creado:

```bash
# perfil de desarrollo: nvidia-smi ausente es WARNING, exit 0
.venv/bin/python monitoring/preflight.py --profile dev

# perfil de servidor: todas las comprobaciones son obligatorias
.venv/bin/python monitoring/preflight.py --profile server --json

# comprobación completa contra el host desplegado
.venv/bin/python monitoring/preflight.py --profile server \
  --require-listeners 127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000 \
  --textfile-dir /var/lib/node_exporter/textfile_collector --json
```

`preflight.py` integra `validate_prometheus.py` y `validate_operation.py`,
`promtool check config` y `systemd-analyze verify`. Opciones relevantes:

- `--profile {dev,server}`: en `dev` la ausencia de `nvidia-smi`, `promtool` o
  `systemd-analyze` degrada a `WARNING`; en `server` bloquea.
- `--require-listeners host:puerto,...`: falla si algún listener no está en
  `LISTEN` en la dirección indicada (un bind en `0.0.0.0` no satisface
  `127.0.0.1`).
- `--textfile-dir DIR`: comprueba presencia, frescura y contenido del textfile
  NVIDIA.
- `--json`: informe estructurado con estado por comprobación.

Comprobaciones individuales:

```bash
.venv/bin/python monitoring/check_listeners.py \
  --require 127.0.0.1:9100,127.0.0.1:9090,127.0.0.1:3000
.venv/bin/python monitoring/check_nvidia_textfile.py \
  --directory /var/lib/node_exporter/textfile_collector --max-age 45
```

`check_nvidia_textfile.py` exige `local_ai_gpu_scrape_success 1` y las métricas
GPU nucleares; el margen de 45 s cubre con holgura el timer de 15 s.

La reversión de este despliegue se describe en [`rollback.md`](rollback.md).
