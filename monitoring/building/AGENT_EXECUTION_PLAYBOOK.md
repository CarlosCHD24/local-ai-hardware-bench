# Playbook de ejecución para agentes locales

Este documento convierte los pilotos en reglas de decisión. Se aplica antes de
marcar una tarea como `ready` y durante cualquier reintento.

## Clasificación antes de asignar

| Clase | Alcance | Asignación a Hermes |
|---|---|---|
| A | Función pura, parser o validador de un archivo | Sí, con fixtures literales |
| B | CLI pequeña o integración de un archivo | Sí, con firma y ejemplos de salida |
| C | Varios archivos, estados persistentes o escritura atómica | Sólo con esqueleto y contratos separados |
| D | Diseño, servicios, secretos o despliegue | No; requiere diseñador u operador |

Una tarea C nunca mezcla en una misma entrega una interfaz nueva, reglas de
estado y rollback. Se divide por comportamiento observable. La tarea debe
declarar el orden de las piezas y cada pieza debe tener su propio contrato
inmutable.

## Puerta de diseño

El diseñador no marca una tarea como `ready` hasta confirmar:

1. Un único archivo técnico o dos como máximo, con una interfaz pública.
2. Entre cuatro y seis comportamientos en el contrato; si hay más, dividir.
3. Fixtures literales para formatos, tiempo, mocks y fallo de escritura.
4. El comando de contrato falla sólo por la funcionalidad aún pendiente, nunca
   por un baseline roto o una dependencia ausente.
5. Para una CLI, lista completa de subcomandos, argumentos, códigos y ejemplos
   exactos de invocación.
6. Para persistencia, protocolo de escritura, punto de fallo simulado y estado
   esperado tras un rollback.

## Ciclo de una ronda

1. Leer sólo tarea, contrato, candidato y resumen de auditoría actual.
2. Ejecutar primero el test de contrato para observar el fallo real.
3. Formular una hipótesis que relacione cada fallo con una línea o invariante.
4. Hacer un cambio pequeño dentro de las rutas permitidas.
5. Ejecutar `py_compile` si procede y el mismo test de contrato.
6. Ejecutar las verificaciones literales completas sólo cuando el contrato pase.

`PASS` exige salidas con código `0` observadas en esa ronda. Una explicación o
un cambio no verificado equivale a `FAIL`.

## Recuperación y escalado

- La primera corrección puede cubrir todos los fallos de una misma causa.
- La segunda debe cambiar la causa raíz observada, no reformular la misma
  corrección.
- Si dos auditorías conservan la misma firma de error, no gastar una tercera
  ronda ciega: marcar `blocked` y devolver el fallo, la hipótesis descartada y
  la división o esqueleto que falta.
- Un error de sintaxis o importación se corrige y se verifica con `py_compile`
  antes de volver a ejecutar contratos.
- El diseñador asume directamente una tarea bloqueada cuando el contrato exige
  rollback, varios reemplazos atómicos o cambios de arquitectura no cubiertos
  por un esqueleto.

## Entrega mínima del agente

```text
RESULT: PASS | FAIL | CONFIG_ERROR
FILES: rutas técnicas modificadas
CONTRACT: comando literal | código observado
OTHER_CHECKS: comando literal | código observado
CAUSE_OR_PENDING: una causa concreta o none
```

El auditor usa comandos y diffs como evidencia; nunca acepta esta entrega por
sí sola.
