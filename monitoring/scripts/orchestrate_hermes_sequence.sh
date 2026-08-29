#!/usr/bin/env bash

set -uo pipefail

repo_dir="${HERMES_REPO_DIR:?HERMES_REPO_DIR is required}"
sequence_job_dir="${HERMES_JOB_DIR:?HERMES_JOB_DIR is required}"
job_id="${HERMES_JOB_ID:?HERMES_JOB_ID is required}"
base_branch="${HERMES_BASE_BRANCH:?HERMES_BASE_BRANCH is required}"
base_commit="${HERMES_BASE_COMMIT:?HERMES_BASE_COMMIT is required}"
worktree_root="${HERMES_WORKTREE_ROOT:?HERMES_WORKTREE_ROOT is required}"
remote="${HERMES_REMOTE:-origin}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
prepare_script="$script_dir/prepare_hermes_task.sh"

manifest_value() {
    local manifest="$1" key="$2"
    sed -n "s/^${key}: *//p" "$manifest" | tail -n 1
}

fail() {
    printf 'FAILED %s\n' "$1" >"$sequence_job_dir/state"
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

main() {
    local task_id task_job_dir manifest worktree worker accepted work_branch
    mkdir -p "$sequence_job_dir"
    test -x "$prepare_script" || fail 'task preparation script is unavailable'
    printf 'RUNNING PREPARATION\n' >"$sequence_job_dir/state"

    for task_id in TASK-002 TASK-003 TASK-004 TASK-005; do
        task_job_dir="$sequence_job_dir/$task_id"
        printf 'PREPARING %s\n' "$task_id" >"$sequence_job_dir/state"
        env HERMES_REPO_DIR="$repo_dir" \
            HERMES_JOB_DIR="$task_job_dir" \
            HERMES_JOB_ID="$job_id" \
            HERMES_TASK_ID="$task_id" \
            HERMES_BASE_BRANCH="$base_branch" \
            HERMES_BASE_COMMIT="$base_commit" \
            HERMES_WORKTREE_ROOT="$worktree_root" \
            HERMES_REMOTE="$remote" \
            bash "$prepare_script" >"$task_job_dir.prepare.log" 2>&1 || \
                fail "$task_id preparation failed"

        manifest="$task_job_dir/$task_id-manifest.yaml"
        worktree="$(manifest_value "$manifest" worktree)"
        worker="$worktree/monitoring/scripts/run_hermes_sequence.sh"
        test -x "$worker" || fail "$task_id worker is unavailable"

        printf 'RUNNING %s\n' "$task_id" >"$sequence_job_dir/state"
        env HERMES_WORKTREE="$worktree" \
            HERMES_JOB_DIR="$task_job_dir" \
            HERMES_JOB_MANIFEST="$manifest" \
            bash "$worker" || fail "$task_id execution failed"

        accepted="$(manifest_value "$manifest" accepted_commit)"
        work_branch="$(manifest_value "$manifest" work_branch)"
        printf '%s\n' "$accepted" | grep -Eq '^[0-9a-f]{40}$' || \
            fail "$task_id did not publish an accepted commit"
        base_commit="$accepted"
        base_branch="$work_branch"
        printf 'ACCEPTED %s %s\n' "$task_id" "$accepted" >"$sequence_job_dir/state"
    done

    printf 'COMPLETE TASK-002 TASK-003 TASK-004 TASK-005 %s\n' "$base_commit" \
        >"$sequence_job_dir/state"
}

if test "${BASH_SOURCE[0]}" = "$0"; then
    main "$@"
fi
