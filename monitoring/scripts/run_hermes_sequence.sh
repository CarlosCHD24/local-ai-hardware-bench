#!/usr/bin/env bash

set -uo pipefail

worktree="${HERMES_WORKTREE:?HERMES_WORKTREE is required}"
job_dir="${HERMES_JOB_DIR:?HERMES_JOB_DIR is required}"
hermes_bin="${HERMES_BIN:-$HOME/.hermes/hermes-agent/venv/bin/hermes}"
profile_dir="${HERMES_PROFILE_DIR:-$HOME/.hermes/profiles/monitoringworker}"
round_limit=3
round_timeout=720
board="$worktree/monitoring/building/TASKS.md"

mkdir -p "$job_dir"
exec >>"$job_dir/runner.log" 2>&1

write_state() {
    printf '%s\n' "$1" >"$job_dir/state"
}

fail() {
    printf '[%s] ERROR: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1"
    write_state "FAILED $1"
    exit 1
}

task_path() {
    case "$1" in
        TASK-002) printf '%s\n' "$worktree/monitoring/building/tasks/TASK-002-crear-parser-markdown.md" ;;
        TASK-003) printf '%s\n' "$worktree/monitoring/building/tasks/TASK-003-crear-validador-tablero.md" ;;
        TASK-004) printf '%s\n' "$worktree/monitoring/building/tasks/TASK-004-automatizar-transiciones.md" ;;
        TASK-005) printf '%s\n' "$worktree/monitoring/building/tasks/TASK-005-crear-colector-nvidia.md" ;;
        *) return 1 ;;
    esac
}

preflight() {
    local secret response_file
    write_state 'PREFLIGHT'
    test -e "$worktree/.git" || fail 'worktree is unavailable'
    test -x "$hermes_bin" || fail 'Hermes executable is unavailable'
    command -v timeout >/dev/null || fail 'external timeout is unavailable'
    command -v curl >/dev/null || fail 'curl is unavailable'
    test -z "$(git -C "$worktree" status --short)" || fail 'worktree is not clean'

    "$hermes_bin" -p monitoringworker --version >/dev/null 2>&1 || \
        fail 'monitoringworker cannot start in detached environment'
    grep -Fq 'provider: custom:local-ai' "$profile_dir/config.yaml" || \
        fail 'local provider is not selected'
    grep -Fq 'default: local-agent' "$profile_dir/config.yaml" || \
        fail 'local-agent is not selected'
    grep -Eq '^fallback_providers: *\[\] *$' "$profile_dir/config.yaml" || \
        fail 'external fallback is not disabled'

    secret="$(sed -n 's/^LOCAL_AI_API_KEY=//p' "$profile_dir/.env" | tail -n 1)"
    test -n "$secret" || fail 'LOCAL_AI_API_KEY is missing from monitoringworker'
    response_file="$job_dir/local-provider-preflight.json"

    curl --fail --silent --show-error --max-time 15 \
        -H "Authorization: Bearer $secret" \
        http://192.168.3.42:8080/v1/models >"$response_file" || \
        fail 'local provider authentication failed'
    grep -q 'local-agent' "$response_file" || fail 'local-agent is not advertised'

    curl --fail --silent --show-error --max-time 90 \
        -H "Authorization: Bearer $secret" \
        -H 'Content-Type: application/json' \
        --data '{"model":"local-agent","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":4,"temperature":0}' \
        http://192.168.3.42:8080/v1/chat/completions >"$response_file" || \
        fail 'minimal local inference failed'
    grep -q '"choices"' "$response_file" || fail 'minimal local inference was invalid'
    rm -f "$response_file"

    printf '[%s] PREFLIGHT provider=custom:local-ai model=local-agent fallback=disabled\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

claim_task() {
    local task_id="$1" file now dependency
    file="$(task_path "$task_id")" || fail "$task_id is unknown"
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    test -f "$file" || fail "$task_id document is missing"
    grep -Fq '| Status | `ready` |' "$file" || fail "$task_id is not ready"

    dependency="$(sed -n 's/^| Depends on | \(.*\) |$/\1/p' "$file")"
    if test "$dependency" != '—'; then
        grep -F "| $dependency |" "$board" | grep -Fq '| `done` |' || \
            fail "$task_id dependency $dependency is not done"
    fi

    sed -i 's/^| Status | `ready` |$/| Status | `in_progress` |/' "$file"
    sed -i 's/^| Owner | — |$/| Owner | Hermes |/' "$file"
    sed -i "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed -i "/^| ${task_id} |/s/| \`ready\` | — |/| \`in_progress\` | Hermes |/" "$board"
}

complete_task() {
    local task_id="$1" file now
    file="$(task_path "$task_id")"
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sed -i 's/^| Status | `in_progress` |$/| Status | `done` |/' "$file"
    sed -i 's/^| Owner | Hermes |$/| Owner | — |/' "$file"
    sed -i "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed -i "/^| ${task_id} |/s/| \`in_progress\` | Hermes |/| \`done\` | — |/" "$board"
}

block_task() {
    local task_id="$1" file now message
    file="$(task_path "$task_id")"
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    message="Bloqueada automáticamente tras tres rondas; consultar los logs del job."
    sed -i 's/^| Status | `in_progress` |$/| Status | `blocked` |/' "$file"
    sed -i 's/^| Owner | Hermes |$/| Owner | — |/' "$file"
    sed -i "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed -i "s/^Sin trabajo pendiente ni bloqueos\.$/$message/" "$file"
    sed -i "/^| ${task_id} |/s/| \`in_progress\` | Hermes |/| \`blocked\` | — |/" "$board"
}

allowed_path() {
    case "$1:$2" in
        TASK-002:monitoring/markdown_table.py|\
        TASK-002:monitoring/tests/test_markdown_table.py|\
        TASK-003:monitoring/taskctl.py|\
        TASK-003:monitoring/tests/test_taskctl.py|\
        TASK-004:monitoring/taskctl.py|\
        TASK-004:monitoring/tests/test_taskctl.py|\
        TASK-005:monitoring/nvidia_metrics.py|\
        TASK-005:monitoring/tests/test_nvidia_metrics.py|\
        TASK-002:monitoring/building/TASKS.md|\
        TASK-003:monitoring/building/TASKS.md|\
        TASK-004:monitoring/building/TASKS.md|\
        TASK-005:monitoring/building/TASKS.md|\
        TASK-002:monitoring/building/tasks/TASK-002-crear-parser-markdown.md|\
        TASK-003:monitoring/building/tasks/TASK-003-crear-validador-tablero.md|\
        TASK-004:monitoring/building/tasks/TASK-004-automatizar-transiciones.md|\
        TASK-005:monitoring/building/tasks/TASK-005-crear-colector-nvidia.md)
            return 0 ;;
        *) return 1 ;;
    esac
}

check_allowed_paths() {
    local task_id="$1" path actual
    actual="$(
        cd "$worktree" || exit 1
        { git diff --name-only; git diff --cached --name-only; git ls-files --others --exclude-standard; } | sort -u
    )" || return 1
    for path in $actual; do
        allowed_path "$task_id" "$path" || {
            printf 'forbidden path: %s\n' "$path" >&2
            return 1
        }
    done
}

intent_to_add() {
    local task_id="$1" path
    case "$task_id" in
        TASK-002) path='monitoring/markdown_table.py monitoring/tests/test_markdown_table.py' ;;
        TASK-003|TASK-004) path='monitoring/taskctl.py monitoring/tests/test_taskctl.py' ;;
        TASK-005) path='monitoring/nvidia_metrics.py monitoring/tests/test_nvidia_metrics.py' ;;
    esac
    for path in $path; do
        test ! -f "$worktree/$path" || git -C "$worktree" add -N -- "$path"
    done
}

audit_task() {
    local task_id="$1" audit_log="$2"
    : >"$audit_log"
    intent_to_add "$task_id" >>"$audit_log" 2>&1 || return 1
    check_allowed_paths "$task_id" >>"$audit_log" 2>&1 || return 1
    (
        cd "$worktree" || exit 1
        case "$task_id" in
            TASK-002)
                python3 -m unittest monitoring.contract_tests.test_markdown_table_contract
                ;;
            TASK-003)
                python3 -m unittest monitoring.contract_tests.test_markdown_table_contract monitoring.contract_tests.test_taskctl_contract
                python3 -m monitoring.taskctl validate --root .
                python3 -m monitoring.taskctl --help
                ;;
            TASK-004)
                python3 -m unittest monitoring.contract_tests.test_taskctl_contract monitoring.contract_tests.test_taskctl_transitions_contract
                python3 -m monitoring.taskctl validate --root .
                python3 -m monitoring.taskctl --help
                ;;
            TASK-005)
                python3 -m unittest monitoring.contract_tests.test_nvidia_metrics_contract
                python3 -m monitoring.nvidia_metrics --help
                ;;
        esac
        python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
        git diff --check
    ) >>"$audit_log" 2>&1
}

make_prompt() {
    local task_id="$1" round="$2" audit_log="$3" prompt="$4" file
    file="$(task_path "$task_id")"
    {
        printf 'Completa %s de forma autónoma. Esta es la ronda %s de 3.\n\n' "$task_id" "$round"
        printf 'Trabaja sólo en el directorio recibido mediante --in. La primera herramienta es `pwd`. '
        printf 'No busques otros repositorios. El proveedor autorizado es exclusivamente local-agent.\n\n'
        printf 'Lee monitoring/AGENTS.md, monitoring/building/README.md, '
        printf 'monitoring/building/HERMES_TASK_GUIDE.md y %s.\n' "${file#"$worktree/"}"
        printf 'La tarea ya está reclamada. Modifica sólo sus archivos técnicos permitidos. '
        printf 'No modifiques monitoring/building/, monitoring/contract_tests/, no hagas commits y no pidas confirmación.\n\n'
        if test "$round" -gt 1; then
            printf 'La auditoría independiente de la ronda anterior falló. Corrige todos estos fallos literales:\n\n'
            tail -n 160 "$audit_log"
            printf '\n'
        fi
        printf 'Ejecuta las verificaciones de la tarea y termina con el formato breve de HERMES_TASK_GUIDE.md.\n'
    } >"$prompt"
}

commit_task() {
    local task_id="$1" message="$2"
    check_allowed_paths "$task_id" || fail "$task_id has forbidden changes before commit"
    (
        cd "$worktree" || exit 1
        git add -A
        git -c user.name='Hermes Orchestrator' \
            -c user.email='hermes-orchestrator@local' commit -m "$message"
    ) || fail "$task_id commit failed"
}

run_task() {
    local task_id="$1" round prompt output audit_log run_code previous_audit
    claim_task "$task_id"
    previous_audit=''

    for round in 1 2 3; do
        write_state "RUNNING $task_id ROUND $round/$round_limit"
        prompt="$job_dir/$task_id-round-$round.prompt"
        output="$job_dir/$task_id-round-$round-hermes.log"
        audit_log="$job_dir/$task_id-round-$round-audit.log"
        make_prompt "$task_id" "$round" "$previous_audit" "$prompt"
        printf '[%s] Starting %s round %s/%s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round" "$round_limit"

        timeout --signal=TERM --kill-after=30s "${round_timeout}s" \
            "$hermes_bin" -p monitoringworker chat \
            --query-file "$prompt" \
            --in "$worktree" \
            --max-turns 12 \
            --run-budget 600 \
            --reasoning none \
            --toolsets terminal,file \
            --quiet \
            --source cli >"$output" 2>&1
        run_code=$?
        printf '[%s] %s round %s Hermes exit=%s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round" "$run_code"

        if audit_task "$task_id" "$audit_log"; then
            complete_task "$task_id"
            if test -f "$worktree/monitoring/taskctl.py"; then
                (cd "$worktree" && python3 -m monitoring.taskctl validate --root .) \
                    >>"$audit_log" 2>&1 || fail "$task_id final state validation failed"
            fi
            commit_task "$task_id" "Complete $task_id with Hermes"
            printf '[%s] Completed %s in round %s\n' \
                "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round"
            return 0
        fi

        printf '[%s] Audit failed for %s round %s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round"
        previous_audit="$audit_log"
    done

    block_task "$task_id"
    commit_task "$task_id" "Block $task_id after three Hermes rounds"
    write_state "BLOCKED $task_id AFTER $round_limit ROUNDS"
    printf '[%s] Blocked %s after %s rounds\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round_limit"
    exit 1
}

printf '[%s] Sequential Hermes job started\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
preflight
if test "${HERMES_PREFLIGHT_ONLY:-0}" = '1'; then
    write_state 'PREFLIGHT_OK provider=custom:local-ai model=local-agent fallback=disabled'
    printf '[%s] Preflight-only run completed\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    exit 0
fi
run_task TASK-002
run_task TASK-003
run_task TASK-004
run_task TASK-005
write_state 'COMPLETE TASK-002 TASK-003 TASK-004 TASK-005'
printf '[%s] Sequential Hermes job completed\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
