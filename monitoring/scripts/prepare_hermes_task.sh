#!/usr/bin/env bash

set -uo pipefail

repo_dir="${HERMES_REPO_DIR:?HERMES_REPO_DIR is required}"
job_dir="${HERMES_JOB_DIR:?HERMES_JOB_DIR is required}"
job_id="${HERMES_JOB_ID:?HERMES_JOB_ID is required}"
task_id="${HERMES_TASK_ID:?HERMES_TASK_ID is required}"
base_branch="${HERMES_BASE_BRANCH:?HERMES_BASE_BRANCH is required}"
base_commit="${HERMES_BASE_COMMIT:?HERMES_BASE_COMMIT is required}"
worktree_root="${HERMES_WORKTREE_ROOT:?HERMES_WORKTREE_ROOT is required}"
remote="${HERMES_REMOTE:-origin}"

fail() {
    printf 'FAILED %s\n' "$1" >"$job_dir/state"
    printf 'ERROR: %s\n' "$1" >&2
    exit 1
}

validate_inputs() {
    printf '%s\n' "$job_id" | grep -Eq '^[A-Za-z0-9._-]+$' || fail 'invalid job id'
    printf '%s\n' "$task_id" | grep -Eq '^TASK-[0-9]{3}$' || fail 'invalid task id'
    printf '%s\n' "$remote" | grep -Eq '^[A-Za-z0-9._-]+$' || fail 'invalid remote name'
    printf '%s\n' "$base_branch" | grep -Eq '^[A-Za-z0-9._/-]+$' || fail 'invalid base branch'
    printf '%s\n' "$base_commit" | grep -Eq '^[0-9a-f]{40}$' || fail 'invalid base commit'
    git -C "$repo_dir" rev-parse --git-dir >/dev/null 2>&1 || fail 'repository is unavailable'
}

write_allowed_paths() {
    case "$task_id" in
        TASK-002) printf '  - monitoring/markdown_table.py\n' ;;
        TASK-003|TASK-004) printf '  - monitoring/taskctl.py\n' ;;
        TASK-005) printf '  - monitoring/nvidia_metrics.py\n' ;;
        *) return 1 ;;
    esac
}

write_contract_checks() {
    case "$task_id" in
        TASK-002)
            printf '  - python3 -m unittest monitoring.contract_tests.test_markdown_table_contract\n'
            ;;
        TASK-003)
            printf '  - python3 -m unittest monitoring.contract_tests.test_markdown_table_contract monitoring.contract_tests.test_taskctl_contract\n'
            printf '  - python3 -m monitoring.taskctl validate --root .\n'
            ;;
        TASK-004)
            printf '  - python3 -m unittest monitoring.contract_tests.test_taskctl_contract monitoring.contract_tests.test_taskctl_transitions_contract\n'
            printf '  - python3 -m monitoring.taskctl validate --root .\n'
            ;;
        TASK-005)
            printf '  - python3 -m unittest monitoring.contract_tests.test_nvidia_metrics_contract\n'
            ;;
        *) return 1 ;;
    esac
    printf "  - python3 -m unittest discover -s monitoring/tests -p 'test_*.py'\n"
    printf '  - git diff --check\n'
}

write_manifest() {
    local manifest="$1" work_branch="$2" execution_commit="$3" worktree="$4"
    {
        printf 'schema: 1\n'
        printf 'job_id: %s\n' "$job_id"
        printf 'task_id: %s\n' "$task_id"
        printf 'repository: remote:%s\n' "$remote"
        printf 'remote: %s\n' "$remote"
        printf 'base_branch: %s\n' "$base_branch"
        printf 'base_commit: %s\n' "$base_commit"
        printf 'work_branch: %s\n' "$work_branch"
        printf 'execution_commit: %s\n' "$execution_commit"
        printf 'accepted_commit: null\n'
        printf 'result: prepared\n'
        printf 'result_commit: null\n'
        printf 'worktree: %s\n' "$worktree"
        printf 'profile: monitoringworker\n'
        printf 'allowed_paths:\n'
        write_allowed_paths
        printf 'contract_checks:\n'
        write_contract_checks
    } >"$manifest"
}

main() {
    local remote_base work_branch worktree runner execution_commit manifest remote_execution
    mkdir -p "$job_dir" "$worktree_root"
    repo_dir="$(cd "$repo_dir" && pwd -P)" || fail 'repository path is invalid'
    worktree_root="$(cd "$worktree_root" && pwd -P)" || fail 'worktree root is invalid'
    validate_inputs

    printf 'PREPARING %s\n' "$task_id" >"$job_dir/state"
    git -C "$repo_dir" fetch "$remote" \
        "refs/heads/$base_branch:refs/remotes/$remote/$base_branch" || fail 'Git fetch failed'
    remote_base="$(git -C "$repo_dir" rev-parse "$remote/$base_branch^{commit}")" || \
        fail 'remote base branch is unavailable'
    test "$remote_base" = "$base_commit" || fail 'remote base branch does not match base commit'

    work_branch="hermes/$task_id/$job_id"
    worktree="$worktree_root/$job_id-$task_id"
    test ! -e "$worktree" || fail 'task worktree already exists'
    git -C "$repo_dir" show-ref --verify --quiet "refs/heads/$work_branch" && \
        fail 'local work branch already exists'
    git -C "$repo_dir" ls-remote --exit-code --heads "$remote" "$work_branch" >/dev/null 2>&1 && \
        fail 'remote work branch already exists'

    git -C "$repo_dir" worktree add -b "$work_branch" "$worktree" "$base_commit" || \
        fail 'task worktree could not be created'
    runner="$worktree/monitoring/scripts/run_hermes_sequence.sh"
    test -x "$runner" || fail 'task worker is unavailable in base commit'

    env HERMES_WORKTREE="$worktree" HERMES_JOB_DIR="$job_dir" \
        bash -c 'source "$1"; task_preflight "$2" && claim_task "$2" && commit_task "$2" "Claim $2 for Hermes"' \
        prepare-task "$runner" "$task_id" || fail 'task claim commit failed'

    execution_commit="$(git -C "$worktree" rev-parse HEAD)" || fail 'execution commit is unavailable'
    git -C "$worktree" push --set-upstream "$remote" "$work_branch" || \
        fail 'execution branch could not be published'
    git -C "$worktree" fetch "$remote" \
        "refs/heads/$work_branch:refs/remotes/$remote/$work_branch" || \
        fail 'published execution branch could not be fetched'
    remote_execution="$(git -C "$worktree" rev-parse "$remote/$work_branch^{commit}")" || \
        fail 'published execution branch is unavailable'
    test "$remote_execution" = "$execution_commit" || \
        fail 'published execution branch does not match execution commit'

    manifest="$job_dir/$task_id-manifest.yaml"
    write_manifest "$manifest" "$work_branch" "$execution_commit" "$worktree" || \
        fail 'manifest could not be generated'
    env HERMES_WORKTREE="$worktree" HERMES_JOB_DIR="$job_dir" HERMES_JOB_MANIFEST="$manifest" \
        bash -c 'source "$1"; load_manifest && verify_git_manifest "$2" clean && check_claimed_task "$2"' \
        verify-task "$runner" "$task_id" || fail 'generated manifest verification failed'

    printf 'PREPARED %s %s\n' "$task_id" "$execution_commit" >"$job_dir/state"
    printf 'manifest=%s\nworktree=%s\nwork_branch=%s\nexecution_commit=%s\n' \
        "$manifest" "$worktree" "$work_branch" "$execution_commit"
}

if test "${BASH_SOURCE[0]}" = "$0"; then
    main "$@"
fi
