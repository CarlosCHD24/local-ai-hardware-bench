# Manifiesto de ejecución de Hermes

El orquestador genera una copia por job fuera del worktree. No contiene
credenciales. Todos los valores deben estar resueltos; Hermes no interpreta
marcadores ni selecciona ramas.

## Datos

```yaml
schema: 1
job_id: JOB-ID
task_id: TASK-NNN
repository: URL-SIN-CREDENCIALES
remote: origin
base_branch: RAMA-PUBLICADA
base_commit: SHA-COMPLETO
work_branch: hermes/TASK-NNN/JOB-ID
execution_commit: SHA-COMPLETO
accepted_commit: null
result: prepared
result_commit: null
worktree: RUTA-ABSOLUTA
profile: monitoringworker
allowed_paths:
  - RUTA-TECNICA
contract_checks:
  - COMANDO-LITERAL
```

`base_commit` contiene documentación y contratos publicados.
`execution_commit` añade únicamente la reclamación de la tarea y es el `HEAD`
limpio que recibe Hermes. El orquestador completa `result`, `result_commit` y,
si la auditoría pasa, `accepted_commit`.

## Preflight Git generado

El orquestador sustituye los valores y entrega comandos literales equivalentes
a los siguientes:

```bash
pwd
git fetch --prune origin
git branch --show-current
git rev-parse HEAD
git rev-parse origin/hermes/TASK-NNN/JOB-ID
git merge-base --is-ancestor SHA-BASE SHA-EJECUCION
git status --porcelain
```

Resultados obligatorios:

- `pwd` coincide con `worktree`;
- la rama coincide con `work_branch`;
- `HEAD` y la referencia remota coinciden con `execution_commit`;
- `execution_commit` desciende de `base_commit`;
- el estado está vacío antes de la primera ronda.

Cualquier discrepancia produce `CONFIG_ERROR`. Hermes no ejecuta `pull`,
`reset`, cambios de rama, fusiones, commits ni pushes. En una ronda correctiva,
el candidato puede ensuciar sólo `allowed_paths`; commits y referencias deben
seguir coincidiendo con el manifiesto.

## Publicación

Tras una auditoría correcta, el orquestador actualiza estado y evidencias,
crea y publica `accepted_commit` en `work_branch`. La siguiente tarea recibe un
manifiesto nuevo y una rama nueva basada en ese commit. La fusión a la rama
principal es una decisión posterior del orquestador o mantenedor.

Si se agotan las rondas, publica el commit `blocked` como `result_commit`, deja
`accepted_commit: null` y detiene la secuencia.
