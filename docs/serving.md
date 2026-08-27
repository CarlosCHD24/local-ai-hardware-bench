# Servidor de inferencia local

Este despliegue convierte el sobremesa NVIDIA en un servidor de inferencia
OpenAI-compatible para clientes de la red local. La orquestación del agente y
sus herramientas permanecen en el Mac o el Honor; el sobremesa sólo recibe
mensajes y genera tokens.

## Perfil de referencia

El perfil inicial está ajustado al Ryzen 7 5800X, 32 GiB de RAM y RTX 3060 de
12 GB ya medidos por el proyecto:

- Qwen2.5 7B Instruct `Q4_K_M` completamente en CUDA.
- Dos ranuras con *continuous batching*.
- Contexto total de 8192 tokens, repartido entre las ranuras activas.
- Flash Attention y cachés K/V `q8_0` para contener el uso de VRAM.
- Caché de prompts, plantillas Jinja y métricas Prometheus.
- API HTTP compatible con OpenAI, protegida por clave y sin interfaz web.

Este perfil prioriza latencia interactiva y dos clientes ocasionales. Antes de
subir el contexto o el número de ranuras hay que medir VRAM, latencia y tasa de
tokens con la carga concurrente real.

## Instalación en Ubuntu/NVIDIA

Partiendo de un checkout ya preparado con el modelo 7B:

```bash
./bin/build-local-ai-server
install -d -m 700 ~/.config/local-ai ~/.config/systemd/user
openssl rand -hex -out ~/.config/local-ai/api-keys 32
chmod 600 ~/.config/local-ai/api-keys
install -m 600 deploy/server/desktop-rtx3060-12gb.env.example \
  ~/.config/local-ai/server.env
install -m 644 deploy/systemd/local-ai-server.service \
  ~/.config/systemd/user/local-ai-server.service
systemctl --user daemon-reload
systemctl --user enable --now local-ai-server.service
```

Comprobaciones locales:

```bash
systemctl --user status local-ai-server.service
curl --fail http://192.168.3.42:8080/health
API_KEY=$(<~/.config/local-ai/api-keys)
curl --fail -H "Authorization: Bearer ${API_KEY}" \
  http://192.168.3.42:8080/v1/models
nvidia-smi
```

`systemctl --user enable` hace que el servicio arranque al iniciar sesión. Para
que también arranque sin una sesión abierta, un administrador debe ejecutar una
sola vez:

```bash
sudo loginctl enable-linger carlos
```

Si UFW está activo, limita el puerto a la LAN en vez de abrirlo globalmente:

```bash
sudo ufw allow from 192.168.3.0/24 to any port 8080 proto tcp
```

Conviene reservar `192.168.3.42` para el sobremesa en el DHCP del router. La
API usa HTTP: la clave y las peticiones no deben atravesar redes no confiables.
Para acceso remoto se debe usar WireGuard/Tailscale o un proxy HTTPS, nunca
publicar directamente el puerto 8080 en Internet.

## Clientes

Tras copiar la clave a un fichero con permisos `0600`, cualquier SDK compatible
con OpenAI puede apuntar a:

```text
base_url = http://192.168.3.42:8080/v1
model = local-agent
```

Están disponibles tanto `/v1/chat/completions` como `/v1/responses`; este
último facilita la integración con clientes modernos orientados a agentes.

Ejemplo con `curl`:

```bash
API_KEY=$(<~/.config/local-ai/desktop-api-key)
curl --fail http://192.168.3.42:8080/v1/chat/completions \
  -H "Authorization: Bearer ${API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "local-agent",
    "messages": [{"role": "user", "content": "Responde: API_OK"}],
    "temperature": 0,
    "max_tokens": 16
  }'
```

El servidor acepta *tool calling* mediante la plantilla Jinja del modelo, pero
no se habilitan las herramientas experimentales integradas ni un proxy MCP. El
cliente agente debe validar y ejecutar cada herramienta con sus propios
permisos; el modelo sólo propone llamadas.

## Operación

```bash
systemctl --user restart local-ai-server.service
journalctl --user -u local-ai-server.service -f
curl -H "Authorization: Bearer $(<~/.config/local-ai/api-keys)" \
  http://192.168.3.42:8080/metrics
```

Para cambiar de modelo, edita `LOCAL_AI_SERVER_MODEL` y
`LOCAL_AI_SERVER_ALIAS` en `~/.config/local-ai/server.env`, reinicia el servicio
y vuelve a verificar `/v1/models`. Mantener un solo modelo residente evita que
varios runtimes compitan por la VRAM. Ollama puede seguir instalado, pero no se
debe cargar un modelo allí mientras este servicio use la GPU.
