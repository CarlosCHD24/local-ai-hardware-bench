#!/usr/bin/env bash

set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

printf 'audit-aggregation-ok\n'
