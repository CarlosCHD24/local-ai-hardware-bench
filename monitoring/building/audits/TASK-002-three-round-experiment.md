# Experimento de tres rondas: TASK-002

## Resultado

- Fecha: 2026-08-28 UTC.
- Modelo efectivo: `local-agent`, sin fallback.
- Veredicto real: rechazado; el parser seguía fallando el contrato.
- El job se detuvo antes de que TASK-003 produjera código.

El orquestador marcó TASK-002 como `done` por un defecto propio: ejecutó todas
las comprobaciones, pero devolvió únicamente el código de `git diff --check`.
Ese último comando pasó y ocultó los tests fallidos. Codex detectó la
incoherencia, detuvo el job y corrigió el agregador.

## Medida

| Ronda | Llamadas | Duración | Hallazgo al cerrar |
|---|---:|---:|---|
| 1 | 12 | 4:24 | Contrato, import y espacios finales |
| 2 | 12 | 4:55 | Archivo auxiliar fuera de alcance |
| 3 | 12 | 5:18 | Contrato del separador aún fallaba |
| Total | 36 | 14:37 | No aceptable |

Los tests propios duplicados añadieron unas 160 líneas y generaron errores que
los cinco tests inmutables ya cubrían. Las rondas 2 y 3 volvieron a leer
documentación general y consumieron varias llamadas antes de editar.

## Cambios derivados

1. Acumular el código de todas las verificaciones; un fallo nunca puede quedar
   oculto por un comando posterior correcto.
2. Ejecutar todas las comprobaciones aunque exista un path prohibido, para que
   la siguiente ronda reciba el diagnóstico completo.
3. Añadir una prueba de regresión del agregador con secuencias fallo→éxito y
   éxito→éxito.
4. Reducir rondas correctivas a 8 turnos, 360 segundos internos y 480 externos.
5. No releer documentación general durante reparaciones; enviar sólo candidato
   y hasta 100 líneas de auditoría.
6. Eliminar espacios finales mecánicamente antes de auditar.
7. No pedir tests propios cuando los contratos inmutables cubren toda la matriz.
8. Expresar el separador exacto como `^:?-{3,}:?$` en la tarea.

## Conclusión

Tres rondas no fueron suficientes con el protocolo anterior. El número de
rondas no era el principal problema: se desperdiciaron llamadas en contexto
duplicado, tests redundantes y diagnósticos incompletos. Debe repetirse TASK-002
con el protocolo corregido antes de decidir si tres rondas son el límite
adecuado.
