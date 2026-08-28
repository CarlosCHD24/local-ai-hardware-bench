# Monitorización del servidor local de IA

## Estado del documento

- Estado: propuesta técnica inicial.
- Versión: 0.1.
- Fecha: 2026-08-28.
- Ámbito inicial: servidor Ubuntu con NVIDIA GeForce RTX 3060 y `llama-server`.

## 1. Objetivo

Construir un sistema local de observabilidad para el servidor de inferencia de
IA que permita consultar en tiempo real y conservar un histórico de:

- disponibilidad y estado del servicio;
- llamadas, errores, concurrencia y latencia;
- tokens de entrada, tokens reutilizados desde caché y tokens generados;
- rendimiento de procesamiento y generación;
- uso de CPU, RAM, GPU, VRAM, disco y red;
- temperatura, potencia y energía consumida;
- coste eléctrico real o estimado en euros;
- configuración activa del modelo y del runtime.

El sistema debe funcionar dentro de la red local, no almacenar prompts ni
respuestas y sobrevivir a los reinicios de `llama-server` sin perder el
histórico ya recopilado.

## 2. Situación de partida

El servidor de inferencia ya ofrece:

- API compatible con OpenAI mediante `llama-server`;
- autenticación por clave;
- endpoint `/health`;
- endpoint Prometheus `/metrics`, activado con `--metrics`;
- registros operativos en el journal de `systemd`;
- telemetría de la RTX 3060 accesible mediante `nvidia-smi`.

Las métricas nativas incluyen contadores globales de tokens, tiempos de
procesamiento, rendimiento y estado de las ranuras. No incluyen un contador
persistente de llamadas HTTP, estados de respuesta ni histogramas de latencia.

El equipo tampoco expone actualmente un contador de energía de CPU mediante
RAPL o `hwmon`. La potencia reportada por `nvidia-smi` corresponde únicamente a
la GPU y no representa el consumo eléctrico total del servidor.

No hay todavía Prometheus, Grafana ni exportadores de sistema instalados.

## 3. Alcance

### 3.1. Incluido en el MVP

- Despliegue local y reproducible de Prometheus y Grafana.
- Recopilación de métricas de `llama-server` con autenticación.
- Métricas de Linux: CPU, RAM, swap, disco, red, carga y uptime.
- Métricas NVIDIA: uso de GPU, VRAM, temperatura, relojes y potencia.
- Persistencia local del histórico.
- Dashboard principal y vistas de inferencia, hardware y energía.
- Tarifa eléctrica configurable en euros por kWh.
- Cálculo separado de coste GPU medido y coste total estimado.
- Alertas visuales básicas.
- Configuración y dashboards versionados en Git.

### 3.2. Fase posterior

- Gateway HTTP para métricas exactas por llamada.
- Latencia p50, p95 y p99, tiempo hasta el primer token y códigos HTTP.
- Desglose opcional por cliente, endpoint o modelo.
- Integración con un enchufe inteligente o UPS con medición eléctrica.
- Tarifas eléctricas por periodos horarios.
- Notificaciones externas.
- Comparación entre telemetría real y resultados de benchmark.

### 3.3. Fuera de alcance

- Almacenar prompts, respuestas, herramientas invocadas o contenido del usuario.
- Exponer el panel o los exportadores directamente a Internet.
- Evaluar la calidad de las respuestas del modelo.
- Calcular amortización de hardware en el MVP.
- Sustituir la suite de benchmarks existente.

## 4. Arquitectura propuesta

```text
Clientes OpenAI-compatible
          |
          v
  Gateway de métricas             Fase posterior
          |
          v
     llama-server ---- /metrics -------------------+
                                                     |
     node_exporter ---- sistema Linux --------------+--> Prometheus --> Grafana
                                                     |
     NVIDIA exporter -- nvidia-smi -----------------+
                                                     |
     Medidor eléctrico -----------------------------+   Opcional
```

### 4.1. Prometheus

Responsable de recopilar y conservar las series temporales. Debe:

- consultar `llama-server` cada 5 segundos;
- consultar el exportador NVIDIA cada 5 segundos;
- consultar las métricas generales del sistema cada 15 segundos;
- leer la clave de `llama-server` desde un fichero protegido;
- conservar inicialmente 30 días de datos;
- aplicar reglas de grabación para tasas, energía y costes derivados;
- tratar correctamente los reinicios de contadores de `llama-server`.

Prometheus se ejecutará en el mismo servidor durante el MVP. Esta decisión
simplifica el despliegue, pero implica que el panel no estará disponible si el
equipo completo se apaga. Una sonda externa desde otro dispositivo de la red
podrá añadirse más adelante para detectar ese caso.

### 4.2. Grafana

Responsable de visualización y alertas. La fuente Prometheus y los dashboards
se provisionarán desde archivos incluidos en este directorio para que la
instalación sea reproducible.

El acceso se limitará a la red local y requerirá autenticación. Grafana no
conocerá la clave de la API de inferencia: sólo consultará a Prometheus.

### 4.3. Métricas del sistema

`node_exporter` será la fuente principal de métricas del host:

- utilización y carga de CPU;
- memoria disponible, usada y swap;
- espacio y actividad de disco;
- tráfico y errores de red;
- uptime;
- sensores publicados por el kernel cuando estén disponibles.

La salud y el consumo del servicio `local-ai-server.service` se incorporarán
mediante métricas de `systemd`, cgroup o un exportador específico si el nivel de
detalle de `node_exporter` no resulta suficiente.

### 4.4. Métricas NVIDIA

Un exportador basado en `nvidia-smi` publicará como mínimo:

- uso de GPU y controlador de memoria;
- VRAM usada, libre y total;
- temperatura;
- potencia instantánea y límite de potencia;
- estado de rendimiento y frecuencias;
- errores de recopilación y antigüedad de la última muestra.

La potencia instantánea se integrará en el tiempo para producir un contador de
energía GPU. El contador debe conservar continuidad entre muestras y reiniciarse
de forma detectable si se reinicia el exportador.

El MVP comenzará con un colector mínimo en Python y biblioteca estándar que
convierta una muestra de `nvidia-smi` a formato Prometheus. La exposición para
scrape —servidor HTTP o textfile collector— se decidirá en una tarea posterior.
Esto permite validar primero nombres, unidades, errores y privacidad sin unir
implementación, despliegue y operación en un mismo cambio.

### 4.5. Gateway de llamadas

El gateway se incorporará después del primer MVP y será el único punto de
entrada de los clientes. Reenviará las solicitudes a `llama-server` sin alterar
su contenido y publicará:

- llamadas totales por endpoint y resultado;
- llamadas activas;
- duración completa de la llamada;
- tiempo hasta el primer token para respuestas en streaming;
- tokens de entrada y salida cuando la respuesta incluya `usage`;
- respuestas canceladas, truncadas o fallidas.

No se usarán la clave completa, la IP del cliente, el prompt o la respuesta
como etiquetas. Si se necesita distinguir clientes, se configurará un
identificador estable y de baja cardinalidad que no contenga secretos.

## 5. Catálogo inicial de métricas

### 5.1. Inferencia nativa de `llama-server`

| Métrica | Tipo | Uso previsto |
|---|---|---|
| `llamacpp:prompt_tokens_total` | contador | Tokens de prompt procesados sin caché |
| `llamacpp:prompt_tokens_cached_total` | contador | Tokens reutilizados desde caché |
| `llamacpp:tokens_predicted_total` | contador | Tokens generados |
| `llamacpp:prompt_seconds_total` | contador | Tiempo acumulado procesando prompts |
| `llamacpp:tokens_predicted_seconds_total` | contador | Tiempo acumulado generando |
| `llamacpp:prompt_tokens_seconds` | indicador | Rendimiento actual de prompt |
| `llamacpp:predicted_tokens_seconds` | indicador | Rendimiento actual de generación |
| `llamacpp:requests_processing` | indicador | Solicitudes en procesamiento |
| `llamacpp:requests_deferred` | indicador | Solicitudes en espera |
| `llamacpp:n_tokens_max` | indicador acumulativo | Máximo contexto observado |

Estas métricas son globales desde el último arranque del proceso. Prometheus
deberá utilizar incrementos y tasas para presentar periodos como “última hora”
o “hoy” y reconocer reinicios del contador.

### 5.2. Métricas derivadas

Se definirán reglas con nombres propios y estables:

- `local_ai_input_tokens_total`: prompt procesado más caché reutilizada;
- `local_ai_all_tokens_total`: entrada más generación;
- `local_ai_cache_ratio`: caché dividida entre entrada total;
- `local_ai_prompt_tokens_per_second`;
- `local_ai_generated_tokens_per_second`;
- `local_ai_gpu_energy_kwh_total`;
- `local_ai_gpu_cost_eur_total`;
- `local_ai_estimated_server_energy_kwh_total`;
- `local_ai_estimated_server_cost_eur_total`;
- `local_ai_cost_eur_per_million_generated_tokens`.

Las series de coste y energía llevarán una etiqueta o metadato de procedencia:
`gpu_measured`, `server_estimated` o `server_measured`. El panel nunca mezclará
estas categorías en una cifra que parezca consumo real.

### 5.3. Métricas del futuro gateway

Los nombres definitivos se cerrarán durante su diseño. Como contrato inicial:

- `local_ai_http_requests_total{endpoint,status_class}`;
- `local_ai_http_requests_active{endpoint}`;
- `local_ai_http_request_duration_seconds` como histograma;
- `local_ai_http_time_to_first_token_seconds` como histograma;
- `local_ai_request_input_tokens_total`;
- `local_ai_request_output_tokens_total`;
- `local_ai_request_failures_total{reason}`.

Las etiquetas estarán acotadas. Nunca se incluirán identificadores de petición,
texto libre o valores que creen una serie nueva por cada llamada.

## 6. Energía y coste

### 6.1. Fórmulas

La energía se obtiene integrando potencia en el tiempo:

```text
energia_kWh = suma(potencia_W * intervalo_horas) / 1000
coste_eur   = energia_kWh * tarifa_eur_kWh
```

La tarifa se almacenará en configuración, no en el dashboard, y tendrá una
fecha de vigencia. El valor inicial será una tarifa única aportada por el
usuario.

### 6.2. Niveles de precisión

1. **GPU medida:** utiliza la potencia reportada por la RTX 3060. Es precisa
   para la GPU, pero excluye CPU, placa, RAM, discos y pérdidas de la fuente.
2. **Servidor estimado:** combina GPU medida con una base y un componente CPU
   configurables. Debe mostrarse siempre como estimación.
3. **Servidor medido:** utiliza un enchufe o UPS que entregue potencia y energía
   total. Será la referencia preferida cuando exista.

El coste por token se calculará sólo para intervalos con generación. Debe
evitar divisiones por cero y mostrar claramente si incluye consumo en reposo.

## 7. Dashboards

### 7.1. Resumen

- estado del servidor y antigüedad de la última muestra;
- modelo, cuantización, contexto y ranuras activas;
- llamadas actuales y, cuando exista el gateway, llamadas de hoy;
- tokens de entrada, caché y salida de hoy;
- tasa de acierto de caché;
- rendimiento de prompt y generación;
- GPU, VRAM, temperatura y potencia;
- energía y coste de hoy;
- proyección de coste mensual.

### 7.2. Inferencia

- tokens por minuto y acumulados;
- procesamiento frente a generación;
- caché procesada frente a reutilizada;
- ranuras ocupadas y solicitudes diferidas;
- máximo contexto observado;
- llamadas, errores, latencia y tiempo hasta el primer token cuando exista el
  gateway;
- reinicios del proceso y discontinuidades de contadores.

### 7.3. Hardware

- CPU total y por núcleo;
- RAM, swap y memoria del servicio;
- uso de GPU y VRAM;
- temperatura, potencia, límite y frecuencias;
- disco, red y carga del sistema;
- correlación entre actividad de inferencia y presión de hardware.

### 7.4. Energía y coste

- potencia instantánea;
- energía por hora, día y mes;
- coste diario y mensual;
- proyección a final de mes;
- coste por llamada y por millón de tokens cuando estén disponibles;
- comparación explícita entre medición y estimación.

## 8. Alertas iniciales

- `llama-server` no responde o el scrape falla.
- El servicio se ha reiniciado.
- Exportador sin muestras recientes.
- VRAM por encima del umbral configurado.
- Temperatura GPU por encima del umbral configurado.
- Solicitudes diferidas durante un periodo sostenido.
- Disco con menos del porcentaje libre configurado.
- Prometheus no puede escribir o se aproxima al límite de retención.

Los umbrales térmicos y de capacidad se configurarán después de observar una
línea base; no se fijarán valores arbitrarios en el código.

## 9. Seguridad y privacidad

- Todos los componentes escucharán únicamente en localhost o en la LAN.
- El firewall limitará el acceso a los puertos de administración.
- La clave de `llama-server` permanecerá en un fichero `0600` fuera de Git.
- Prometheus leerá la credencial desde ese fichero.
- Grafana tendrá autenticación y no se publicará de forma anónima.
- No se recopilarán cuerpos HTTP, prompts, respuestas ni cabeceras sensibles.
- Los logs aplicarán redacción de claves y tokens de autorización.
- Las etiquetas Prometheus serán estables y de baja cardinalidad.
- Los datos y credenciales no se enviarán a servicios externos.

## 10. Estructura prevista del subproyecto

```text
monitoring/
├── README.md
├── building/
│   ├── README.md
│   ├── TASKS.md
│   ├── TASK_TEMPLATE.md
│   └── tasks/
├── prometheus/
│   ├── prometheus.yml
│   ├── recording-rules.yml
│   └── alert-rules.yml
├── grafana/
│   ├── dashboards/
│   └── provisioning/
├── systemd/
├── scripts/
├── gateway/                 # Fase posterior
└── tests/
```

No se crearán todos estos componentes hasta comenzar su fase correspondiente.

## 11. Fases de implementación

### Fase 1: infraestructura y telemetría base

- Añadir Prometheus y Grafana como servicios reproducibles.
- Añadir exportadores de sistema y NVIDIA.
- Configurar scrape autenticado de `llama-server`.
- Crear reglas para tasas de tokens, caché y energía GPU.
- Validar persistencia y reinicios de contadores.

### Fase 2: dashboard MVP

- Provisionar las cuatro vistas definidas.
- Configurar tarifa eléctrica constante.
- Añadir costes GPU y estimación de servidor claramente diferenciados.
- Añadir alertas básicas y documentación operativa.

### Fase 3: observabilidad por llamada

- Diseñar e implementar el gateway.
- Conservar compatibilidad con los endpoints OpenAI utilizados actualmente.
- Medir llamadas, estados, latencia y streaming.
- Cambiar `llama-server` a un puerto interno y mantener el puerto público del
  gateway estable para los clientes.

### Fase 4: medición eléctrica real

- Seleccionar e integrar un medidor local.
- Sustituir la estimación total por energía medida.
- Conservar ambas series durante un periodo para calibrar el modelo estimado.

## 12. Criterios de aceptación del MVP

El MVP se considerará completo cuando:

1. Grafana muestre datos actuales e históricos sin acceso a Internet.
2. Un reinicio de `llama-server` no elimine el histórico anterior.
3. Se distingan tokens procesados, reutilizados y generados.
4. Se visualicen CPU, RAM, GPU, VRAM, temperatura y potencia.
5. Se pueda configurar una tarifa y obtener coste diario y mensual.
6. Toda cifra de energía indique si es medida o estimada.
7. El panel detecte la caída de `llama-server` y exportadores.
8. Ninguna clave, prompt o respuesta aparezca en métricas o logs del sistema de
   monitorización.
9. La instalación y los dashboards puedan reconstruirse desde los archivos
   versionados en este directorio.

## 13. Decisiones pendientes

- Tarifa inicial en EUR/kWh.
- Retención definitiva después de medir el volumen real de series.
- Exposición del colector NVIDIA mediante HTTP frente a textfile collector.
- Método para observar el cgroup del servicio de usuario de `systemd`.
- Dispositivo de medición eléctrica total, si se incorpora.
- Nivel de desglose por cliente permitido por privacidad.

Estas decisiones no bloquean la implementación de la telemetría base.
