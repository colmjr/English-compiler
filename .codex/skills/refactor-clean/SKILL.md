---
name: refactor-clean
description: Refactor, clean up, and fix code for a specified pull request. Use when the user invokes /refactor-clean (or $refactor-clean) and provides a PR number, PR URL, or PR branch to improve code quality while preserving intended behavior.
---

# Refactor Clean

Take one required argument: a PR identifier (`123`, full PR URL, or branch name).

## Workflow

1. Resolve the PR argument.
- Parse a numeric value as a PR number.
- Parse a GitHub PR URL as repository + PR number.
- Parse a branch name as the working branch when it already exists locally.
- Ask for clarification when the argument is missing or ambiguous.

2. Check out the PR branch.
- Prefer `gh pr checkout <number>` when GitHub CLI access is available.
- Fallback to:
```bash
git fetch origin pull/<number>/head:pr-<number>
git switch pr-<number>
```
- Determine the PR base branch with `gh pr view <number> --json baseRefName` when available, otherwise use merge-base against the default branch.

3. Review the change set before editing.
- Inspect the diff and changed files.
- Identify high-value improvements:
  - correctness bugs and edge cases
  - duplicated logic
  - naming clarity and readability
  - dead code and unused paths
  - missing or weak tests around changed behavior

4. Implement safe refactors and fixes.
- Keep behavior stable unless explicitly fixing a bug.
- Keep edits focused on files touched by the PR or directly related dependencies.
- Follow existing project conventions for style and architecture.

5. Validate changes.
- Run targeted tests for changed modules first.
- Run broader tests, lint, and format checks when practical.
- If checks cannot run, state exactly which checks were skipped and why.

6. Report results clearly.
- State the PR argument resolved and branch used.
- Summarize refactors/fixes made.
- List validation commands run and outcomes.
- Call out residual risks and suggested follow-up tasks.

## Guardrails

- Avoid destructive git operations unless explicitly requested.
- Avoid unrelated rewrites outside the PR scope.
- Prefer minimal, low-risk refactors when behavior impact is uncertain.
- Ask for a fallback input (branch or patch link) if PR retrieval fails.
