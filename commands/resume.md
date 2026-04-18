---
description: Legacy compatibility entry for the official /pickup command. Prefer /pickup target.com.
---

# /resume

`/resume` remains available as a legacy compatibility entry.

Use `/pickup target.com` for the primary command going forward.

## Why

`/pickup` is the official primary command. `/resume` is kept only for compatibility semantics because `/resume` is a reserved Claude Code command.

## Usage

```text
/pickup target.com
```

## Notes

- `/resume` maps to the same continue-hunt flow.
- New docs and examples should use `/pickup`.
