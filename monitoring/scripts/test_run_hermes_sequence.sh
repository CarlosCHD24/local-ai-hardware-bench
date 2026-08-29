#!/usr/bin/env bash

set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT

HERMES_WORKTREE=/tmp/not-used \
HERMES_JOB_DIR=/tmp/not-used \
    source "$script_dir/run_hermes_sequence.sh"

AUDIT_FAILED=0
run_check false
run_check true
test "$AUDIT_FAILED" -eq 1

AUDIT_FAILED=0
run_check true
run_check true
test "$AUDIT_FAILED" -eq 0

worktree="$test_root/worktree"
job_dir="$test_root/job"
mkdir -p "$worktree/monitoring" "$job_dir"
git -C "$worktree" init -q
git -C "$worktree" config user.name 'Runner Test'
git -C "$worktree" config user.email 'runner-test@local'
printf 'baseline\n' >"$worktree/monitoring/tracked-helper.py"
git -C "$worktree" add monitoring/tracked-helper.py
git -C "$worktree" commit -q -m baseline

printf 'changed\n' >"$worktree/monitoring/tracked-helper.py"
printf 'temporary\n' >"$worktree/monitoring/debug_table.py"
test "$(forbidden_paths TASK-002 | wc -l | tr -d ' ')" -eq 2
quarantine_forbidden_changes TASK-002 2 >/dev/null

test "$(cat "$worktree/monitoring/tracked-helper.py")" = 'baseline'
test ! -e "$worktree/monitoring/debug_table.py"
test "$(cat "$job_dir/TASK-002-round-2-forbidden/monitoring/tracked-helper.py")" = 'changed'
test "$(cat "$job_dir/TASK-002-round-2-forbidden/monitoring/debug_table.py")" = 'temporary'
check_allowed_paths TASK-002

printf 'audit-aggregation-and-quarantine-ok\n'
