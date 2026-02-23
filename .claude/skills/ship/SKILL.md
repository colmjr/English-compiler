---
name: ship
description: Run tests, commit changes, push a branch, and create a PR. The standard workflow for shipping work.
argument-hint: "[optional: branch name or PR title]"
---

# Ship Feature

You are shipping: **$ARGUMENTS**

## Phase 1: Run Tests

Run the core test suites to ensure everything passes:

```bash
python -m tests.run
python -m tests.run_algorithms
python -m tests.run_parity
```

If any test fails, stop and report the failure. Do NOT ship broken code.

## Phase 2: Update Documentation

Check if any documentation needs updating for the changes being shipped:
- README.md
- docs/
- CLI help text (if CLI behavior changed)
- CLAUDE.md test list (if new test files were added)

## Phase 3: Stage and Commit

1. Review all changed files with `git status` and `git diff`
2. Stage relevant files (avoid staging unrelated changes, secrets, or generated artifacts)
3. Create a descriptive commit message summarizing the changes

## Phase 4: Push and Create PR

1. If on `main`, create a new feature branch first (never push to main directly)
2. Push the branch with `git push -u origin <branch>`
3. Create a PR with `gh pr create`:
   - Short, descriptive title (under 70 characters)
   - Body with a summary of changes and test results

Show the PR URL when done.
