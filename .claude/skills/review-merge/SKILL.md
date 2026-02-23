# Review and Merge PRs

Review and merge open PRs with code review, testing, and merge safety checks.

**Usage**: `/review-merge` (all open PRs) or `/review-merge <number>` (specific PR)

## Steps

### 1. Identify PRs to review

- If a PR number is given, review that single PR.
- Otherwise, list all open PRs with `gh pr list` and review each one (oldest first, unless one depends on another).

### 2. For each PR, run these checks in parallel

- **Code Review:** Read the diff with `gh pr diff <number>`. Check for logic errors, dropped functionality, missing edge cases, consistency with existing patterns, and verify documentation is updated where needed.
- **Test Verification:** Checkout the PR branch, run the full test suite (`python -m tests.run`, `python -m tests.run_algorithms`, `python -m tests.run_parity`, `python -m tests.test_short_circuit`, `python -m tests.test_lower`, `python -m tests.test_break_continue`, `python -m tests.test_try_catch`, `python -m tests.test_switch`, `python -m tests.test_type_convert`, `python -m tests.test_import`, `python -m tests.test_javascript`, `python -m tests.test_rust`, `python -m tests.test_go`, `python -m tests.test_lint`), and report any failures with root cause analysis.
- **Merge Safety:** Check for merge conflicts with main. Verify no conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) remain in any files. Confirm the PR doesn't break existing functionality.

### 3. Report and merge

- If all checks pass: report results and **ask before merging**.
- If any check fails: report the issues but do NOT merge.
- Merge with `gh pr merge <number> --merge` when approved.
- Pull latest main: `git checkout main && git pull`

### 4. Summary

If reviewing multiple PRs, give a final summary table: PR number, title, status (ready to merge / blocked), and any issues found.
