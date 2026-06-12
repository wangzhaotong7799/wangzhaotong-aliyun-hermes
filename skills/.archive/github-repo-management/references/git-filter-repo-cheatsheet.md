# git-filter-repo Quick Reference

> Install: `pip install git-filter-repo`
> Docs: https://github.com/newren/git-filter-repo

## Common Commands

```bash
# Remove specific files from all history
git filter-repo --path .env --path auth.json --invert-paths --force

# Remove a directory from all history
git filter-repo --path secrets/ --invert-paths --force

# Replace a string across all commits (e.g., accidental commit with AWS key)
git filter-repo --replace-text <(echo 'AKIAIOSFODNN7EXAMPLE==>REDACTED') --force

# Strip large files by size
git filter-repo --strip-blobs-bigger-than 10M --force

# Combine filters
git filter-repo \
  --path .env \
  --path auth.json \
  --path 'secrets.yaml' \
  --invert-paths \
  --force
```

## Post-Cleanup Commands

```bash
# Add remote back (filter-repo removes it)
git remote add origin git@github.com:owner/repo.git

# Force push (all SHAs changed)
git push --force --set-upstream origin main

# Push all branches and tags
git push --force --all origin
git push --force --tags origin
```

## Verification

```bash
# Confirm files are gone
git ls-files .env auth.json
# → (no output)

# Check a specific old commit doesn't contain the file
git ls-tree -r <old-commit-sha> .env
# → (no output if scrubbed)

# Count remaining sensitive strings (if any)
git grep -i 'api_key' HEAD -- '*.yaml' '*.yml' '*.json' '*.py' | head -10
```

## Important Notes

1. **Commits get new SHAs** — this rewrites history. All existing clones are incompatible.
2. **`--force` is required** because filter-repo refuses to run on a repo with a dirty working tree or backups.
3. **Backups exist** as `refs/original/` unless `--no-refs` is used. Verify these are gone: `git for-each-ref refs/original` (should show nothing).
4. **Submodules** need separate treatment — run filter-repo inside each submodule repo.
