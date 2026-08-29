#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf -- "$test_root"' EXIT

remote_repo="$test_root/remote.git"
source_repo="$test_root/source"
job_dir="$test_root/job"
worktree_root="$test_root/worktrees"
job_id='git-workflow-test'

mkdir -p "$source_repo" "$job_dir" "$worktree_root"
cp -R "$project_root/monitoring" "$source_repo/monitoring"
cp "$project_root/.gitignore" "$source_repo/.gitignore"
git init --bare -q "$remote_repo"
git -C "$source_repo" init -q
git -C "$source_repo" checkout -q -b design
git -C "$source_repo" config user.name 'Workflow Test'
git -C "$source_repo" config user.email 'workflow-test@local'
git -C "$source_repo" add .
git -C "$source_repo" commit -q -m 'Published design'
git -C "$source_repo" remote add origin "$remote_repo"
git -C "$source_repo" push -q -u origin design
base_commit="$(git -C "$source_repo" rev-parse HEAD)"
git -C "$source_repo" config --replace-all remote.origin.fetch \
    '+refs/tags/test-only:refs/tags/test-only'

env HERMES_REPO_DIR="$source_repo" \
    HERMES_JOB_DIR="$job_dir" \
    HERMES_JOB_ID="$job_id" \
    HERMES_TASK_ID=TASK-002 \
    HERMES_BASE_BRANCH=design \
    HERMES_BASE_COMMIT="$base_commit" \
    HERMES_WORKTREE_ROOT="$worktree_root" \
    HERMES_REMOTE=origin \
    PYTHONPYCACHEPREFIX="$test_root/pycache" \
    bash "$script_dir/prepare_hermes_task.sh" >"$test_root/prepare.log"

manifest="$job_dir/TASK-002-manifest.yaml"
worktree="$(sed -n 's/^worktree: *//p' "$manifest")"
work_branch="$(sed -n 's/^work_branch: *//p' "$manifest")"
execution_commit="$(sed -n 's/^execution_commit: *//p' "$manifest")"
runner="$worktree/monitoring/scripts/run_hermes_sequence.sh"

test "$(git -C "$worktree" rev-parse HEAD)" = "$execution_commit"
test "$(git -C "$source_repo" rev-parse "origin/$work_branch")" = "$execution_commit"
test -z "$(git -C "$worktree" status --porcelain)"
grep -Fq '| Status | `in_progress` |' \
    "$worktree/monitoring/building/tasks/TASK-002-crear-parser-markdown.md"

env HERMES_WORKTREE="$worktree" HERMES_JOB_DIR="$job_dir" HERMES_JOB_MANIFEST="$manifest" \
    bash -c 'source "$1"; load_manifest && verify_git_manifest TASK-002 clean && check_claimed_task TASK-002' \
    verify-clean "$runner"

drift_repo="$test_root/drift"
git clone -q --branch "$work_branch" "$remote_repo" "$drift_repo"
git -C "$drift_repo" config user.name 'Remote Drift'
git -C "$drift_repo" config user.email 'remote-drift@local'
printf 'unexpected\n' >"$drift_repo/REMOTE_DRIFT.txt"
git -C "$drift_repo" add REMOTE_DRIFT.txt
git -C "$drift_repo" commit -q -m 'Advance remote unexpectedly'
git -C "$drift_repo" push -q origin "$work_branch"

if env HERMES_WORKTREE="$worktree" HERMES_JOB_DIR="$job_dir" HERMES_JOB_MANIFEST="$manifest" \
    bash -c 'source "$1"; load_manifest && verify_git_manifest TASK-002 clean' \
    verify-drift "$runner"; then
    printf 'remote drift was not detected\n' >&2
    exit 1
fi

publish_job_dir="$test_root/publish-job"
publish_job_id='git-publish-test'
mkdir -p "$publish_job_dir"
env HERMES_REPO_DIR="$source_repo" \
    HERMES_JOB_DIR="$publish_job_dir" \
    HERMES_JOB_ID="$publish_job_id" \
    HERMES_TASK_ID=TASK-002 \
    HERMES_BASE_BRANCH=design \
    HERMES_BASE_COMMIT="$base_commit" \
    HERMES_WORKTREE_ROOT="$worktree_root" \
    HERMES_REMOTE=origin \
    PYTHONPYCACHEPREFIX="$test_root/pycache" \
    bash "$script_dir/prepare_hermes_task.sh" >"$test_root/publish-prepare.log"

publish_manifest="$publish_job_dir/TASK-002-manifest.yaml"
publish_worktree="$(sed -n 's/^worktree: *//p' "$publish_manifest")"
publish_branch="$(sed -n 's/^work_branch: *//p' "$publish_manifest")"
publish_runner="$publish_worktree/monitoring/scripts/run_hermes_sequence.sh"
env HERMES_WORKTREE="$publish_worktree" \
    HERMES_JOB_DIR="$publish_job_dir" \
    HERMES_JOB_MANIFEST="$publish_manifest" \
    bash -c 'source "$1"; load_manifest; complete_task TASK-002; commit_task TASK-002 "Accept TASK-002 test"; publish_task_result accepted' \
    publish-result "$publish_runner"

accepted_commit="$(sed -n 's/^accepted_commit: *//p' "$publish_manifest")"
test "$(sed -n 's/^result: *//p' "$publish_manifest")" = 'accepted'
test "$(sed -n 's/^result_commit: *//p' "$publish_manifest")" = "$accepted_commit"
test "$(git -C "$source_repo" rev-parse "origin/$publish_branch")" = "$accepted_commit"

printf 'git-bootstrap-drift-and-publication-ok\n'
