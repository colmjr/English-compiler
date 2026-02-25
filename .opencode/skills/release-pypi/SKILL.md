---
name: release-pypi
description: Bump the package version, run tests, and create a GitHub Release that triggers PyPI publishing.
---

# Release to PyPI

Bump the package version, run tests, and create a GitHub Release that triggers PyPI publishing.

**Usage**: `/release-pypi <version-or-bump>`
- Explicit version: `/release-pypi 1.8.0`
- Bump keyword: `/release-pypi patch`, `/release-pypi minor`, `/release-pypi major`

## Steps

### 1. Parse the version argument

- Read the current version from `english_compiler/coreil/versions.py` (the `PACKAGE_VERSION` line).
- If the argument is `patch`, `minor`, or `major`, compute the next version:
  - `patch`: `1.7.3` -> `1.7.4`
  - `minor`: `1.7.3` -> `1.8.0`
  - `major`: `1.7.3` -> `2.0.0`
- If the argument is an explicit version (e.g. `1.8.0`):
  - Validate it matches `X.Y.Z` format (all integers).
  - Validate it is strictly greater than the current version.
- Print the version transition (e.g. `1.7.3 -> 1.7.4`) and confirm with the user before proceeding.

### 2. Run the full test suite

Run all core test suites. Abort immediately if any test fails.

```bash
python -m tests.run
python -m tests.run_algorithms
python -m tests.run_parity
python -m tests.test_short_circuit
python -m tests.test_lower
python -m tests.test_break_continue
python -m tests.test_try_catch
python -m tests.test_switch
python -m tests.test_type_convert
python -m tests.test_import
python -m tests.test_javascript
python -m tests.test_rust
python -m tests.test_go
python -m tests.test_lint
```

### 3. Bump the version

Edit `english_compiler/coreil/versions.py` — change the `PACKAGE_VERSION = "..."` line to the new version.

### 4. Commit the version bump

```bash
git add english_compiler/coreil/versions.py
git commit -m "Bump version to X.Y.Z"
```

### 5. Create a PR, merge, then tag

Since branch protection prevents direct pushes to main:

1. Create a branch: `git checkout -b version/X.Y.Z`
2. Push the branch: `git push -u origin version/X.Y.Z`
3. Create a PR: `gh pr create --title "Bump version to X.Y.Z" --body "Version bump for PyPI release."`
4. Merge the PR: `gh pr merge <number> --merge`
5. Return to main: `git checkout main && git pull origin main`
6. Create and push the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`

### 6. Create a GitHub Release

```bash
gh release create vX.Y.Z --generate-notes
```

This triggers the existing `.github/workflows/publish.yml` workflow, which publishes to PyPI.

### 7. Verify the publish workflow

Poll the workflow until it completes:

```bash
gh run list --workflow=publish.yml --limit=1
```

- If the status is `completed` and conclusion is `success`, report that the release is live on PyPI.
- If the workflow fails, proceed to the rollback steps below.

### 8. Rollback (only if the publish workflow failed)

If the workflow failed, walk the user through these rollback steps:

1. **Delete the GitHub Release:**
   ```bash
   gh release delete vX.Y.Z --yes
   ```

2. **Delete the remote and local tag:**
   ```bash
   git push origin --delete vX.Y.Z
   git tag -d vX.Y.Z
   ```

3. **Revert the version bump on main:**
   ```bash
   git checkout main && git pull origin main
   ```
   Then create a revert branch, revert the merge commit, push, and merge via PR:
   ```bash
   git checkout -b revert/vX.Y.Z
   git revert --mainline 1 <merge-commit-hash>
   git push -u origin revert/vX.Y.Z
   gh pr create --title "Revert version bump to X.Y.Z" --body "Publish workflow failed. Reverting version bump."
   gh pr merge <number> --merge
   git checkout main && git pull origin main
   ```

4. **Confirm cleanup:** Verify with `gh release list` and `git tag -l 'vX.Y.Z'` that the release and tag are gone.

5. **Report** the workflow failure URL (`gh run view <run-id> --web`) so the user can debug the root cause before retrying.
