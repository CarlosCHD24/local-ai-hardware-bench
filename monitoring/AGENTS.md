# Instrucciones para agentes

Estas reglas se aplican a todo el árbol `monitoring/`.

1. Lee `README.md`, `building/README.md`, `building/TASKS.md` y el documento de
   la tarea antes de modificar archivos.
2. Reclama la tarea y mantén sincronizados su estado y `building/TASKS.md`.
3. Limita los cambios al alcance y a los archivos permitidos por la tarea.
4. No modifiques ni reinicies el servidor de inferencia salvo autorización
   explícita en la tarea.
5. No guardes claves, prompts, respuestas, cabeceras de autorización ni datos
   personales en código, métricas, pruebas o logs.
6. Ejecuta las verificaciones indicadas y resume el resultado en la tarea.
7. No hagas `commit`, `push` ni fusiones; el orquestador auditará el worktree.

Si una instrucción esencial es ambigua o exige ampliar el alcance, marca la
tarea como `blocked` y documenta el motivo en `Handoff`.
