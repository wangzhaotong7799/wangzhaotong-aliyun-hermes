# exclude-newer Dependency Resolution Failure (verbatim)

Observed 2026-08-07 during v0.19.0 → v0.20.0 upgrade (3407 commits behind, git install).

## Failure signature (tail of `hermes update` output)

```
× No solution found when resolving dependencies:
  ╰─▶ Because there is no version of cryptography==48.0.1 and
      hermes-agent==0.20.0 depends on cryptography==48.0.1, we can conclude
      that hermes-agent==0.20.0 cannot be used.
      And because only hermes-agent==0.20.0 is available and you require
      hermes-agent, we can conclude that your requirements are unsatisfiable.

hint: `cryptography` was filtered by `exclude-newer` to only include packages
uploaded before 2026-07-24T01:07:11.563595362Z. Consider using
`exclude-newer-package` to override the cutoff for this package.
✗ Update failed: Command '['/root/.hermes/bin/uv', 'pip', 'install', '-e', '.']'
returned non-zero exit status 1.
```

Preceding warnings give the real reason (missing upload-date metadata):
```
warning: cryptography-50.0.0-cp39-abi3-musllinux_1_2_x86_64.whl is missing an
upload date, but user provided: 2026-07-24T01:07:11.506224663Z
warning: cryptography-50.0.0-cp39-abi3-win_amd64.whl is missing an upload date, ...
```

## Relevant pyproject.toml (before fix)

```toml
exclude-newer = "14 days"
exclude-newer-package = { vercel = false, nemo-relay = false, huggingface_hub = false }
```

`exclude-newer = "14 days"` → cutoff = now − 14d. cryptography wheels lack
upload dates in the uv index → filtered → version 48.0.1 unresolvable.

## Applied fix

```toml
exclude-newer-package = { vercel = false, nemo-relay = false, huggingface_hub = false, cryptography = false }
```

Then re-ran install directly (git pull had already succeeded):
```bash
cd /root/.hermes/hermes-agent
/root/.hermes/bin/uv pip install -e . --python /root/.hermes/hermes-agent/venv/bin/python
```

## Takeaways

- `exclude-newer-package` entry = "never filter this package by upload date" (`false` = no cutoff override needed, just exempt it).
- The `14 days` pin lives in pyproject.toml under `[tool.uv]`-adjacent settings; uv reads it from the project config, not from CLI flags, so the fix is a project-file edit, not a CLI flag.
- This failure can hit ANY pinned dependency whose wheels are missing upload-date metadata in the index — cryptography was just the one that broke. Grep the failure for the `filtered by exclude-newer` phrase to recognize the class.
- The pyproject.toml edit is local-only: a future `hermes update` git-pull reverts it or conflicts. Re-apply when the same signature recurs.
