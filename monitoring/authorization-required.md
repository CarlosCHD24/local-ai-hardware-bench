# Autorización necesaria para continuar el despliegue

El código, los contratos y los artefactos de configuración de `monitoring/`
están preparados. Para pasar de preparación a despliegue real hace falta
autorizar expresamente las siguientes acciones en el servidor objetivo.

## Alcance de la autorización

1. Acceso administrativo al servidor Ubuntu que ejecutará `llama-server`.
2. Instalación de Prometheus, Grafana y `node_exporter` desde las fuentes de
   paquetes que el administrador apruebe.
3. Creación de `/var/lib/node_exporter/textfile_collector`, con propietario y
   permisos mínimos para `node_exporter`.
4. Instalación y activación de estas unidades systemd:
   - `node-exporter.service`;
   - `local-ai-nvidia-metrics.service`;
   - `local-ai-nvidia-metrics.timer`.
5. Creación del fichero de clave de lectura de métricas para `llama-server` en
   `/etc/local-ai-monitoring/llama-api-key`, fuera de Git y con permisos `0600`.
6. Recarga de systemd y habilitación de los servicios y temporizador anteriores.

## Límites de seguridad

- No se abrirán puertos de monitoring a Internet.
- Prometheus, Grafana y node_exporter se configurarán para escucha local salvo
  una ampliación de alcance autorizada por separado.
- No se guardarán prompts, respuestas, cabeceras de autorización ni claves en
  el repositorio, métricas o logs.
- La autorización no incluye modificar el servicio `local-ai-server`, su modelo
  ni sus parámetros de inferencia.

## Verificaciones posteriores

Una vez autorizado, se ejecutarán primero el preflight de sólo lectura y la
validación de unidades. Después se comprobarán los endpoints locales, el
scrape de Prometheus y el dashboard sin consultar ni exponer contenido de
inferencias.
