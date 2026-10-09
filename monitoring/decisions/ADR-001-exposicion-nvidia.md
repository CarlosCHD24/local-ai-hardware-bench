# ADR-001: Exposición de métricas NVIDIA mediante textfile collector

- Estado: aceptada
- Fecha: 2026-08-29

## Decisión

El MVP publicará la salida de `python3 -m monitoring.nvidia_metrics` mediante
el directorio de textfile collector de `node_exporter`; no creará un servidor
HTTP propio. Un servicio o temporizador local ejecutará el colector y escribirá
un fichero `.prom` completo en un temporal del mismo directorio antes de
renombrarlo atómicamente al fichero visible por `node_exporter`.

La ruta definitiva se configurará como argumento explícito del adaptador y el
despliegue la limitará a un directorio propiedad del usuario de `node_exporter`.
Prometheus seguirá consultando únicamente el endpoint existente de
`node_exporter` dentro de localhost o de la LAN autorizada.

## Motivos

- Reutiliza el exportador del sistema ya previsto para el MVP y no añade otro
  proceso HTTP, puerto, unidad de firewall ni superficie de autenticación.
- Una ejecución fallida puede dejar una métrica de fallo completa sin que un
  scrape observe un fichero truncado.
- Mantiene la invocación de `nvidia-smi` acotada a una muestra programada, en
  lugar de ejecutarla por cada scrape concurrente.

## Alternativa descartada

Un endpoint HTTP local permitiría activar la muestra bajo demanda, pero exige
gestionar tiempo de respuesta, concurrencia, ciclo de vida y restricciones de
red de un servidor adicional. No aporta una ventaja necesaria para el MVP y se
descarta hasta que haya una necesidad de scrape más frecuente que la permitida
por un temporizador local.

## Consecuencias

TASK-007 implementará el adaptador de escritura atómica y su contrato de
errores. TASK-008 podrá definir el scrape de `node_exporter` y de
`llama-server`; la ubicación concreta de la clave y la herramienta de
validación de Prometheus siguen siendo decisiones separadas.
