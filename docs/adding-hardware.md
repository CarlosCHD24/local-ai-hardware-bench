# Añadir hardware

Un equipo nuevo no requiere cambios de código si usa Linux o macOS y uno de los
backends existentes:

1. Ejecutar `doctor`.
2. Preparar la misma suite.
3. Elegir un `system-id` público.
4. Ejecutar `run`.
5. Validar y revisar privacidad.
6. Comparar o contribuir el directorio de resultados.

Para Linux, sigue primero [`linux.md`](linux.md). Antes de declarar un backend
como probado para una release, completa [`release-checklist.md`](release-checklist.md).

Para soportar otro sistema operativo, hay que implementar un colector en
`src/local_ai_bench/system/`. El colector debe devolver el esquema común y no
incluir identificadores privados.
