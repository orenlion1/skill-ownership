#!/usr/bin/env bash
# Exercise the quality gate end to end on a fixture catalog, including optional model
# execution through a deterministic stub runner. No model is contacted.
set -euo pipefail
cd "$(dirname "$0")/.."
gate=skills/skill-ownership/scripts/run-skill-quality-gate.sh
catalog=tests/fixtures/gate-catalog
stub=tests/fixtures/stub-runner
work=$(mktemp -d "${TMPDIR:-/tmp}/quality-gate-test.XXXXXX")
trap 'case $work in "${TMPDIR:-/tmp}"/quality-gate-test.*) rm -R -- "$work" ;; esac' EXIT
# Fetch the pinned harness once and reuse it for every run below.
harness_dir=${SKILL_QUALITY_HARNESS_DIR:-}
if [[ -z $harness_dir ]]; then
  revision=$(sed -n 's/^readonly harness_revision=//p' "$gate")
  repository=$(sed -n 's/^readonly harness_repository=//p' "$gate")
  harness_dir=$work/harness
  git init --quiet "$harness_dir"
  git -C "$harness_dir" remote add origin "$repository"
  git -C "$harness_dir" fetch --quiet --depth 1 origin "$revision"
  git -C "$harness_dir" checkout --quiet --detach FETCH_HEAD
fi
harness=(--harness-dir "$harness_dir")

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
expect_status() {
  local expected=$1 label=$2; shift 2
  local status=0
  "$@" >"$work/out.log" 2>&1 || status=$?
  if [[ $status -ne $expected ]]; then
    cat "$work/out.log" >&2
    fail "$label: expected exit $expected, got $status"
  fi
  printf 'ok: %s\n' "$label"
}
expect_line() { grep -Fq -- "$1" "$work/out.log" || { cat "$work/out.log" >&2; fail "missing line: $1"; }; }

expect_status 0 'default run plans evals and does not execute them' \
  "$gate" --repository "$catalog" "${harness[@]}"
expect_line 'behavioral dry-run plans: 2'
expect_line 'model execution: not run'
expect_line 'Skill quality gate passed'

expect_status 0 'execution mode grades every eval through the runner' \
  "$gate" --repository "$catalog" "${harness[@]}" --execute-behavioral --runner-dir "$stub" \
  --output-dir "$work/results"
expect_line 'model execution: 2 eval(s) graded across 2 skill(s), 0 skill(s) with a failed or ungraded eval'
[[ -s $work/results/results/alpha.eval-1.grading.json ]] || fail 'grading result was not preserved'

expect_status 0 'execution can be limited to one skill' \
  "$gate" --repository "$catalog" "${harness[@]}" --execute-behavioral --runner-dir "$stub" --skill beta
expect_line 'model execution: 1 eval(s) graded across 1 skill(s)'

expect_status 1 'a failed expectation fails the gate' \
  env STUB_VERDICT=fail "$gate" --repository "$catalog" "${harness[@]}" --execute-behavioral \
  --runner-dir "$stub"
expect_line 'Skill quality gate FAILED: behavioral execution'

expect_status 1 'a missing cases directory fails the gate' \
  "$gate" --repository "$catalog" "${harness[@]}" --cases-dir "$work/missing-cases"
expect_status 2 'runner options without execution mode are rejected' \
  "$gate" --repository "$catalog" --runner-dir "$stub"
expect_status 2 'an out-of-range routing threshold is rejected' \
  "$gate" --repository "$catalog" --min-rank1 101
expect_status 1 'an unknown skill name executes nothing and fails' \
  "$gate" --repository "$catalog" "${harness[@]}" --execute-behavioral --runner-dir "$stub" --skill gamma
printf 'quality gate tests passed\n'
