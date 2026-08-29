# Instrucciones para agentes

Estas reglas se aplican a todo el árbol `monitoring/`.

1. Lee `README.md`, `building/README.md`, `building/TASKS.md`, el documento de
   la tarea y, si existe, el manifiesto del job antes de modificar archivos.
2. En ejecución no orquestada, reclama la tarea y mantén sincronizados su
   estado y `building/TASKS.md`.
3. Limita los cambios al alcance y a los archivos permitidos por la tarea.
4. No modifiques ni reinicies el servidor de inferencia salvo autorización
   explícita en la tarea.
5. No guardes claves, prompts, respuestas, cabeceras de autorización ni datos
   personales en código, métricas, pruebas o logs.
6. Ejecuta las verificaciones indicadas. En ejecución no orquestada, resume el
   resultado en la tarea.
7. No hagas `commit`, `push` ni fusiones; el orquestador auditará el worktree.
8. Si la tarea indica `Execution: orchestrated`, no modifiques documentos de
   workflow dentro de `monitoring/building/`; el orquestador gestiona estado y
   evidencias.
9. Ejecuta los comandos literales desde el directorio indicado. No los
   sustituyas por variantes que pasen desde otro directorio.
10. Para archivos nuevos usa `git add -N -- rutas-permitidas` antes de
    `git diff --check`, sin crear commits.
11. Devuelve `PASS` sólo cuando todos los comandos obligatorios tengan el código
    esperado. Si alguno falla, devuelve `FAIL` y conserva el trabajo parcial.
12. No modifiques `monitoring/contract_tests/`. Son contratos inmutables del
    diseñador y el orquestador los ejecuta después de cada ronda.
13. En ejecución orquestada, la primera herramienta es `pwd` y la primera
    operación Git es el `fetch` exacto del manifiesto. Verifica rama, `HEAD`,
    referencia remota y worktree limpio antes de leer la tarea.
14. No uses `git pull`, `reset`, `checkout`, `switch`, `merge` ni `rebase` para
    corregir una discrepancia. Devuelve `CONFIG_ERROR`; sólo el orquestador
    prepara o sustituye la rama y el worktree.
15. La credencial disponible para Hermes es de sólo lectura. La publicación de
    commits y ramas pertenece al orquestador.

Si una instrucción esencial es ambigua o exige ampliar el alcance, devuelve
`FAIL` con el bloqueo. En ejecución no orquestada, marca además la tarea como
`blocked` y documenta el motivo en `Handoff`.
