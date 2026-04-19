# Upstream Runtime Stability Alignment Design

**Date:** 2026-04-19
**Status:** Draft for review

## Goal

Selectively absorb the highest-value, lowest-risk runtime stability fixes from upstream commit `e079af8` into the local fork without changing the existing hunt workflow, feature surface, or report/output structure.

## Scope

This design is intentionally narrow. It covers only runtime stability and compatibility fixes in the local execution path for hunt-related tools.

### In scope
- Python subprocess cleanup hardening in:
  - `tools/hunt.py`
  - `tools/cve_hunter.py`
  - `tools/zero_day_fuzzer.py`
- Shell timeout/macOS compatibility improvements in:
  - `tools/recon_engine.sh`
  - optionally `tools/vuln_scanner.sh` if needed for consistent timeout behavior
- Dalfox runtime stability improvements where they are clearly safe:
  - bounded timeout behavior
  - conservative dedup before scan input when it does not alter expected findings semantics
- Focused regression coverage for the above behavior

### Out of scope
- Removing legacy tools or refactoring the repo around slash-command-only operation
- Adding new vuln classes or scanner breadth (for example MFA/SAML checks)
- Rewriting docs/prompts beyond what is needed to explain new runtime behavior
- Changing primary CLI semantics, output layout, findings storage layout, or validation/report workflow
- Broad recon pipeline restructuring

## Why this change

The local fork already absorbed the high-value feature updates (`/pickup`, IP/CIDR support, CVSS 4.0). The remaining upstream delta contains a mixed bag of changes, but only the runtime stability fixes are both:
1. materially useful in real hunts, and
2. low enough risk to absorb safely into the local branch.

This keeps alignment practical instead of blindly chasing upstream.

## Design Summary

The implementation will introduce a small, consistent runtime-hardening layer across the affected tools while preserving current behavior.

There are four design rules:
1. **Timeouts must terminate the real spawned workload**, not just the parent wrapper.
2. **macOS/Linux timeout behavior must degrade gracefully**, rather than assuming GNU-only tooling.
3. **Scanner invocations must be bounded**, especially long-running Dalfox paths.
4. **Behavioral drift must be minimized**: same entrypoints, same outputs, same storage, safer execution.

## Architecture

### 1. Python subprocess execution hardening

Affected Python tools currently use simple `subprocess.run(..., shell=True, timeout=...)` style helpers in several places. That is easy to use but weak for cleanup because timeout on the wrapper process may still leave child processes alive.

The new design will standardize these paths on a safer execution pattern:
- launch with a dedicated process group/session
- capture stdout/stderr as today
- on timeout:
  - terminate the whole process group
  - give it a short grace period
  - escalate to hard kill if still alive
- return the same style of `(success, output)` or `(success, stdout, stderr)` result shape each tool already expects

This change is deliberately internal. Callers should not need to know whether cleanup uses `killpg`, `SIGTERM`, `SIGKILL`, or equivalent process-group handling.

### 2. Shell timeout compatibility layer

Upstream specifically addressed macOS timeout behavior. The local repo still assumes GNU `timeout` in shell paths.

Instead of scattering OS-specific checks everywhere, the implementation should use a tiny shell helper approach inside the touched scripts:
- prefer `timeout` when available
- fall back to `gtimeout` when available
- if neither exists, run the command directly and log the degraded mode when needed

This keeps runtime behavior predictable across Linux/macOS without forcing a larger shell framework refactor.

### 3. Dalfox bounded execution

Dalfox is useful but prone to hanging or burning time on repetitive input.

The local design will absorb only the safest parts:
- enforce an upper bound on runtime for the Dalfox stage
- optionally deduplicate candidate URLs conservatively before piping into Dalfox

“Conservative dedup” here means dedup by URL shape that is unlikely to hide real XSS candidates. If this cannot be made obviously safe in the current codepath, timeout-only is preferred over aggressive dedup logic.

### 4. Recon shell stability guardrails

`tools/recon_engine.sh` should absorb only stability-oriented behavior that fits the local nested recon output layout.

Candidate behavior:
- timeout helper compatibility
- safer handling of partial results on interrupted/failed runs when the local file layout makes this low-risk

Anything that assumes upstream-specific recon output or changes discovery semantics should be rejected.

## File-level Design

### `tools/hunt.py`
- Harden helper command execution used by downstream tool launches
- Preserve current return contracts and logging style
- Do not change target classification, report generation flow, or result structure

### `tools/cve_hunter.py`
- Replace fragile timeout handling in `run_cmd()` with process-group-aware cleanup
- Keep current interface and text output intact

### `tools/zero_day_fuzzer.py`
- Harden command execution helpers used by curl-based probing
- Preserve existing detection heuristics and finding format

### `tools/recon_engine.sh`
- Introduce a local timeout wrapper/helper for Linux/macOS
- Only adopt interruption/partial-output protections that fit the current recon tree

### `tools/vuln_scanner.sh`
- Add timeout compatibility only if needed by the implementation
- Add Dalfox runtime bounding
- Add only conservative dedup if demonstrably safe

### Tests
Likely touchpoints:
- existing tests around hunt wrappers / target types if command behavior changes there
- new focused regression tests for timeout cleanup helper behavior where practical
- shell-level behavior tests only if they can be added cheaply and deterministically

## Error Handling

The new behavior should follow these rules:
- timeout returns should still be non-success results, but with clearer cleanup guarantees
- cleanup failures should not crash the entire orchestrator if the original timeout/error path is already known
- degraded compatibility mode (no `timeout`, no `gtimeout`) should be explicit in logs where it matters, but should not break the scan

## Compatibility Constraints

This design must preserve:
- existing command entrypoints
- existing findings directory structure
- existing report generation invocation flow
- current IP/CIDR support
- current `/pickup` and hunt-memory workflow
- current CVSS 4.0 path

No user-facing feature should disappear as a result of this alignment.

## Testing Strategy

Implementation should prove five things:
1. timeout paths no longer leave obvious child processes behind in the affected Python helpers
2. normal success paths still return expected outputs
3. Linux/macOS shell timeout selection behaves predictably
4. Dalfox stage is bounded and does not regress the rest of vuln scanning
5. existing hunt-related regressions still pass

Minimum verification target:
- focused new regression tests for the new helper behavior
- existing hunt-related tests
- full `pytest -q` before merge

## Rejected Alternatives

### Alternative A: absorb only Python cleanup fixes
Rejected because it leaves shell runtime instability and dalfox boundedness unresolved.

### Alternative C: absorb all of upstream `e079af8`
Rejected because it risks importing upstream assumptions that do not cleanly match the local fork’s architecture and file layout.

## Recommended Approach

Proceed with **balanced selective absorption (方案 B)**:
- absorb the subprocess cleanup fixes
- absorb timeout compatibility fixes
- absorb bounded Dalfox execution
- reject broader semantic or architecture drift

This gives the best practical reliability gain for the least risk.

## Success Criteria

The work is successful when:
- hunts are more resilient to timeout/orphan-process failure modes
- Linux/macOS execution is more predictable
- dalfox no longer hangs unbounded in the main scanning path
- all current workflows still behave the same from the user’s perspective
- regression tests remain green
