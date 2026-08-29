#!/usr/bin/env bash

set -uo pipefail

worktree="${HERMES_WORKTREE:?HERMES_WORKTREE is required}"
job_dir="${HERMES_JOB_DIR:?HERMES_JOB_DIR is required}"
hermes_bin="${HERMES_BIN:-$HOME/.hermes/hermes-agent/venv/bin/hermes}"
profile_dir="${HERMES_PROFILE_DIR:-$HOME/.hermes/profiles/monitoringworker}"
job_manifest="${HERMES_JOB_MANIFEST:-}"
round_limit=3
round_timeout=720
board="$worktree/monitoring/building/TASKS.md"
manifest_task_id=''
manifest_remote=''
manifest_base_branch=''
manifest_base_commit=''
manifest_work_branch=''
manifest_execution_commit=''
manifest_worktree=''

write_state() {
    printf '%s\n' "$1" >"$job_dir/state"
}

fail() {
    printf '[%s] ERROR: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1"
    write_state "FAILED $1"
    exit 1
}

sed_in_place() {
    local expression="$1" file="$2" temporary
    temporary="$file.tmp.$$"
    sed "$expression" "$file" >"$temporary" && mv "$temporary" "$file"
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

manifest_value() {
    local key="$1"
    sed -n "s/^${key}: *//p" "$job_manifest" | tail -n 1
}

valid_commit() {
    printf '%s\n' "$1" | grep -Eq '^[0-9a-f]{40}$'
}

load_manifest() {
    test -n "$job_manifest" || {
        printf 'job manifest is required\n' >&2
        return 1
    }
    test -f "$job_manifest" || {
        printf 'job manifest is unavailable: %s\n' "$job_manifest" >&2
        return 1
    }

    manifest_task_id="$(manifest_value task_id)"
    manifest_remote="$(manifest_value remote)"
    manifest_base_branch="$(manifest_value base_branch)"
    manifest_base_commit="$(manifest_value base_commit)"
    manifest_work_branch="$(manifest_value work_branch)"
    manifest_execution_commit="$(manifest_value execution_commit)"
    manifest_worktree="$(manifest_value worktree)"

    printf '%s\n' "$manifest_task_id" | grep -Eq '^TASK-[0-9]{3}$' || return 1
    printf '%s\n' "$manifest_remote" | grep -Eq '^[A-Za-z0-9._-]+$' || return 1
    printf '%s\n' "$manifest_base_branch" | grep -Eq '^[A-Za-z0-9._/-]+$' || return 1
    printf '%s\n' "$manifest_work_branch" | grep -Eq '^hermes/TASK-[0-9]{3}/[A-Za-z0-9._-]+$' || return 1
    valid_commit "$manifest_base_commit" || return 1
    valid_commit "$manifest_execution_commit" || return 1
    test "$(cd "$worktree" 2>/dev/null && pwd -P)" = "$manifest_worktree" || return 1
}

verify_git_manifest() {
    local task_id="$1" mode="$2" actual_branch actual_head remote_head
    git -C "$worktree" fetch --prune "$manifest_remote" || return 1
    actual_branch="$(git -C "$worktree" branch --show-current)" || return 1
    actual_head="$(git -C "$worktree" rev-parse HEAD)" || return 1
    remote_head="$(git -C "$worktree" rev-parse "$manifest_remote/$manifest_work_branch^{commit}")" || return 1

    test "$task_id" = "$manifest_task_id" || return 1
    test "$actual_branch" = "$manifest_work_branch" || return 1
    test "$actual_head" = "$manifest_execution_commit" || return 1
    test "$remote_head" = "$manifest_execution_commit" || return 1
    git -C "$worktree" merge-base --is-ancestor \
        "$manifest_base_commit" "$manifest_execution_commit" || return 1

    if test "$mode" = 'clean'; then
        test -z "$(git -C "$worktree" status --porcelain)" || return 1
    else
        check_allowed_paths "$task_id"
    fi
}

replace_manifest_value() {
    local key="$1" value="$2" temporary
    temporary="$job_manifest.tmp"
    awk -v key="$key" -v value="$value" '
        index($0, key ":") == 1 { print key ": " value; found=1; next }
        { print }
        END { if (!found) print key ": " value }
    ' "$job_manifest" >"$temporary" && mv "$temporary" "$job_manifest"
}

preflight() {
    local secret response_file
    write_state 'PREFLIGHT'
    test -e "$worktree/.git" || fail 'worktree is unavailable'
    load_manifest || fail 'job manifest is invalid'
    verify_git_manifest "$manifest_task_id" clean || \
        fail 'Git state does not match the job manifest'
    test -x "$hermes_bin" || fail 'Hermes executable is unavailable'
    command -v timeout >/dev/null || fail 'external timeout is unavailable'
    command -v curl >/dev/null || fail 'curl is unavailable'

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

    sed_in_place 's/^| Status | `ready` |$/| Status | `in_progress` |/' "$file"
    sed_in_place 's/^| Owner | — |$/| Owner | Hermes |/' "$file"
    sed_in_place "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed_in_place "/^| ${task_id} |/s/| \`ready\` | — |/| \`in_progress\` | Hermes |/" "$board"
}

check_claimed_task() {
    local task_id="$1" file
    file="$(task_path "$task_id")" || return 1
    grep -Fq '| Status | `in_progress` |' "$file" || return 1
    grep -Fq '| Owner | Hermes |' "$file" || return 1
    grep -F "| $task_id |" "$board" | grep -Fq '| `in_progress` | Hermes |'
}

complete_task() {
    local task_id="$1" file now
    file="$(task_path "$task_id")"
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    sed_in_place 's/^| Status | `in_progress` |$/| Status | `done` |/' "$file"
    sed_in_place 's/^| Owner | Hermes |$/| Owner | — |/' "$file"
    sed_in_place "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed_in_place "/^| ${task_id} |/s/| \`in_progress\` | Hermes |/| \`done\` | — |/" "$board"
}

block_task() {
    local task_id="$1" file now message
    file="$(task_path "$task_id")"
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    message="Bloqueada automáticamente tras tres rondas; consultar los logs del job."
    sed_in_place 's/^| Status | `in_progress` |$/| Status | `blocked` |/' "$file"
    sed_in_place 's/^| Owner | Hermes |$/| Owner | — |/' "$file"
    sed_in_place "s/^| Updated | [^|]* |$/| Updated | $now |/" "$file"
    sed_in_place "s/^Sin trabajo pendiente ni bloqueos\.$/$message/" "$file"
    sed_in_place "/^| ${task_id} |/s/| \`in_progress\` | Hermes |/| \`blocked\` | — |/" "$board"
}

allowed_path() {
    case "$1:$2" in
        TASK-002:monitoring/markdown_table.py|\
        TASK-003:monitoring/taskctl.py|\
        TASK-004:monitoring/taskctl.py|\
        TASK-005:monitoring/nvidia_metrics.py|\
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

changed_paths() {
    (
        cd "$worktree" || exit 1
        { git diff --name-only; git diff --cached --name-only; git ls-files --others --exclude-standard; } | sort -u
    )
}

forbidden_paths() {
    local task_id="$1" path
    while IFS= read -r path; do
        test -n "$path" || continue
        allowed_path "$task_id" "$path" || printf '%s\n' "$path"
    done < <(changed_paths)
}

check_allowed_paths() {
    local task_id="$1" path failed=0
    while IFS= read -r path; do
        test -n "$path" || continue
        printf 'forbidden path: %s\n' "$path" >&2
        failed=1
    done < <(forbidden_paths "$task_id")
    return "$failed"
}

quarantine_forbidden_changes() {
    local task_id="$1" round="$2" path destination quarantine_dir
    quarantine_dir="$job_dir/$task_id-round-$round-forbidden"

    while IFS= read -r path; do
        test -n "$path" || continue
        destination="$quarantine_dir/$path"
        mkdir -p "$(dirname "$destination")"

        if git -C "$worktree" cat-file -e "HEAD:$path" 2>/dev/null; then
            if test -e "$worktree/$path"; then
                cp -a "$worktree/$path" "$destination"
            else
                printf 'deleted tracked path\n' >"$destination.deleted"
            fi
            git -C "$worktree" restore --source=HEAD --staged --worktree -- "$path" || return 1
        else
            git -C "$worktree" reset -q HEAD -- "$path" >/dev/null 2>&1 || true
            test ! -e "$worktree/$path" || mv "$worktree/$path" "$destination"
        fi
        printf 'quarantined forbidden path: %s\n' "$path"
    done < <(forbidden_paths "$task_id")
}

intent_to_add() {
    local task_id="$1" path
    case "$task_id" in
        TASK-002) path='monitoring/markdown_table.py' ;;
        TASK-003|TASK-004) path='monitoring/taskctl.py' ;;
        TASK-005) path='monitoring/nvidia_metrics.py' ;;
    esac
    for path in $path; do
        test ! -f "$worktree/$path" || git -C "$worktree" add -N -- "$path"
    done
}

normalize_allowed_python() {
    local task_id="$1" path
    case "$task_id" in
        TASK-002) path='monitoring/markdown_table.py' ;;
        TASK-003|TASK-004) path='monitoring/taskctl.py' ;;
        TASK-005) path='monitoring/nvidia_metrics.py' ;;
    esac
    for path in $path; do
        test ! -f "$worktree/$path" || \
            sed_in_place 's/[[:space:]]\+$//' "$worktree/$path"
    done
}

task_preflight() {
    local task_id="$1"
    (
        cd "$worktree" || exit 1
        case "$task_id" in
            TASK-002)
                python3 -m py_compile monitoring/contract_tests/test_markdown_table_contract.py &&
                    python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
                ;;
            TASK-003)
                python3 -m unittest monitoring.contract_tests.test_markdown_table_contract &&
                    python3 -m py_compile monitoring/contract_tests/test_taskctl_contract.py &&
                    python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
                ;;
            TASK-004)
                python3 -m monitoring.taskctl validate --root . &&
                    python3 -m py_compile monitoring/contract_tests/test_taskctl_transitions_contract.py
                ;;
            TASK-005)
                python3 -c 'import csv, subprocess, unittest' &&
                    python3 -m py_compile monitoring/contract_tests/test_nvidia_metrics_contract.py &&
                    python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
                ;;
            *) return 1 ;;
        esac
    )
}

run_check() {
    "$@" || AUDIT_FAILED=1
    return 0
}

audit_task() {
    local task_id="$1" audit_log="$2" summary
    local failed=0
    : >"$audit_log"
    normalize_allowed_python "$task_id" >>"$audit_log" 2>&1 || failed=1
    intent_to_add "$task_id" >>"$audit_log" 2>&1 || failed=1
    check_allowed_paths "$task_id" >>"$audit_log" 2>&1 || failed=1
    (
        AUDIT_FAILED=0
        cd "$worktree" || exit 1
        case "$task_id" in
            TASK-002)
                run_check python3 -m unittest monitoring.contract_tests.test_markdown_table_contract
                ;;
            TASK-003)
                run_check python3 -m unittest monitoring.contract_tests.test_markdown_table_contract monitoring.contract_tests.test_taskctl_contract
                run_check python3 -m monitoring.taskctl validate --root .
                run_check python3 -m monitoring.taskctl --help
                ;;
            TASK-004)
                run_check python3 -m unittest monitoring.contract_tests.test_taskctl_contract monitoring.contract_tests.test_taskctl_transitions_contract
                run_check python3 -m monitoring.taskctl validate --root .
                run_check python3 -m monitoring.taskctl --help
                ;;
            TASK-005)
                run_check python3 -m unittest monitoring.contract_tests.test_nvidia_metrics_contract
                run_check python3 -m monitoring.nvidia_metrics --help
                ;;
        esac
        run_check python3 -m unittest discover -s monitoring/tests -p 'test_*.py'
        run_check git diff --check
        exit "$AUDIT_FAILED"
    ) >>"$audit_log" 2>&1 || failed=1

    summary="$(grep -E '^(FAIL|ERROR):|^FAILED \(|^forbidden path:' "$audit_log" | sort -u | head -n 50)"
    {
        printf '\n=== AUDIT SUMMARY ===\n'
        test -z "$summary" || printf '%s\n' "$summary"
        if check_allowed_paths "$task_id"; then
            printf 'scope: OK\n'
        else
            failed=1
            printf 'scope: FAILED\n'
        fi
        if test "$failed" -eq 0; then
            printf 'audit-result: PASSED\n'
        else
            printf 'audit-result: FAILED\n'
        fi
    } >>"$audit_log" 2>&1
    return "$failed"
}

make_prompt() {
    local task_id="$1" round="$2" audit_log="$3" prompt="$4" file
    file="$(task_path "$task_id")"
    {
        printf 'Completa %s de forma autónoma. Esta es la ronda %s de 3.\n\n' "$task_id" "$round"
        printf 'Trabaja sólo en el directorio recibido mediante --in. No busques otros repositorios. '
        printf 'El proveedor autorizado es exclusivamente local-agent.\n\n'
        printf 'Lee el manifiesto %s. La primera herramienta es `pwd`. Después ejecuta exactamente:\n' "$job_manifest"
        printf -- '- `git fetch --prune %s`\n' "$manifest_remote"
        printf -- '- `test "$(git branch --show-current)" = "%s"`\n' "$manifest_work_branch"
        printf -- '- `test "$(git rev-parse HEAD)" = "%s"`\n' "$manifest_execution_commit"
        printf -- '- `test "$(git rev-parse %s/%s)" = "%s"`\n' \
            "$manifest_remote" "$manifest_work_branch" "$manifest_execution_commit"
        printf -- '- `git merge-base --is-ancestor %s %s`\n' \
            "$manifest_base_commit" "$manifest_execution_commit"
        if test "$round" -eq 1; then
            printf -- '- `test -z "$(git status --porcelain)"`\n'
        else
            printf 'El candidato puede modificar sólo las rutas técnicas permitidas; no debe haber otros cambios.\n'
        fi
        printf 'Si una comprobación falla, devuelve CONFIG_ERROR sin usar pull, reset, cambios de rama ni fusiones.\n\n'
        if test "$round" -eq 1; then
            printf 'Lee monitoring/AGENTS.md, monitoring/building/README.md, '
            printf 'monitoring/building/HERMES_TASK_GUIDE.md y %s.\n' "${file#"$worktree/"}"
            printf 'La tarea ya está reclamada. Modifica sólo sus archivos técnicos permitidos. '
            printf 'No modifiques monitoring/building/, monitoring/contract_tests/, no hagas commits y no pidas confirmación.\n\n'
        else
            printf 'Es una reparación focalizada sobre el candidato existente. No releas documentación general ni reescribas archivos completos. '
            printf 'Inspecciona sólo los archivos técnicos y corrige los fallos siguientes.\n\n'
            printf 'La auditoría independiente de la ronda anterior falló. Corrige todos estos fallos literales:\n\n'
            tail -n 100 "$audit_log"
            printf '\nLos artefactos fuera de alcance indicados ya fueron puestos en cuarentena. No los recrees.\n\n'
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

publish_task_result() {
    local result="$1" current remote_head
    test -z "$(git -C "$worktree" status --porcelain)" || \
        fail 'worktree is not clean before publication'
    current="$(git -C "$worktree" rev-parse HEAD)" || fail 'cannot resolve result commit'
    git -C "$worktree" push "$manifest_remote" "$manifest_work_branch" || \
        fail 'result branch could not be published'
    git -C "$worktree" fetch --prune "$manifest_remote" || \
        fail 'published branch could not be verified'
    remote_head="$(git -C "$worktree" rev-parse "$manifest_remote/$manifest_work_branch^{commit}")" || \
        fail 'published branch is unavailable'
    test "$remote_head" = "$current" || fail 'published branch does not match result commit'

    replace_manifest_value result "$result" || fail 'manifest result could not be updated'
    replace_manifest_value result_commit "$current" || fail 'manifest result commit could not be updated'
    if test "$result" = 'accepted'; then
        replace_manifest_value accepted_commit "$current" || \
            fail 'manifest accepted commit could not be updated'
    fi
}

run_task() {
    local task_id="$1" round prompt output audit_log run_code previous_audit max_turns run_budget timeout_seconds preflight_log
    preflight_log="$job_dir/$task_id-preflight.log"
    task_preflight "$task_id" >"$preflight_log" 2>&1 || \
        fail "$task_id task preflight failed; baseline is invalid"
    check_claimed_task "$task_id" || fail "$task_id is not claimed in execution_commit"
    previous_audit=''

    for round in 1 2 3; do
        if test "$round" -gt 1; then
            verify_git_manifest "$task_id" candidate || \
                fail "$task_id Git state changed before correction round"
        fi
        write_state "RUNNING $task_id ROUND $round/$round_limit"
        prompt="$job_dir/$task_id-round-$round.prompt"
        output="$job_dir/$task_id-round-$round-hermes.log"
        audit_log="$job_dir/$task_id-round-$round-audit.log"
        make_prompt "$task_id" "$round" "$previous_audit" "$prompt"
        printf '[%s] Starting %s round %s/%s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round" "$round_limit"

        if test "$round" -eq 1; then
            max_turns=12
            run_budget=600
            timeout_seconds="$round_timeout"
        else
            max_turns=8
            run_budget=360
            timeout_seconds=480
        fi

        timeout --signal=TERM --kill-after=30s "${timeout_seconds}s" \
            "$hermes_bin" -p monitoringworker chat \
            --query-file "$prompt" \
            --in "$worktree" \
            --max-turns "$max_turns" \
            --run-budget "$run_budget" \
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
            publish_task_result accepted
            printf '[%s] Completed %s in round %s\n' \
                "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round"
            return 0
        fi

        printf '[%s] Audit failed for %s round %s\n' \
            "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round"
        previous_audit="$audit_log"
        quarantine_forbidden_changes "$task_id" "$round" >>"$audit_log" 2>&1 || \
            fail "$task_id forbidden changes could not be quarantined"
    done

    block_task "$task_id"
    commit_task "$task_id" "Block $task_id after three Hermes rounds"
    publish_task_result blocked
    write_state "BLOCKED $task_id AFTER $round_limit ROUNDS"
    printf '[%s] Blocked %s after %s rounds\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$task_id" "$round_limit"
    exit 1
}

main() {
    mkdir -p "$job_dir"
    exec >>"$job_dir/runner.log" 2>&1
    printf '[%s] Hermes task job started\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    preflight
    if test "${HERMES_PREFLIGHT_ONLY:-0}" = '1'; then
        write_state 'PREFLIGHT_OK provider=custom:local-ai model=local-agent fallback=disabled'
        printf '[%s] Preflight-only run completed\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        return 0
    fi
    run_task "$manifest_task_id"
    write_state "COMPLETE $manifest_task_id"
    printf '[%s] Hermes task job completed\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

if test "${BASH_SOURCE[0]}" = "$0"; then
    main "$@"
fi
