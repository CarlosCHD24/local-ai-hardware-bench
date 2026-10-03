# Despliegue local de monitoring

Copiar los ficheros de `monitoring/systemd/` al directorio de unidades del
sistema, crear `/var/lib/node_exporter/textfile_collector` con el usuario de
node_exporter y verificar las unidades con `systemd-analyze verify` antes de
habilitarlas. La clave de llama-server se mantiene fuera de Git en
`/etc/local-ai-monitoring/llama-api-key` con permisos `0600`.

Prometheus, node_exporter y Grafana escuchan sólo en localhost según los
artefactos versionados. No se debe abrir ningún puerto de monitoring a Internet.
