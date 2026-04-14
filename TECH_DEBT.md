# Tech Debt & Outstanding Review Items

Items identified during the April 2026 design pattern review. Ordered by priority.

---

## High Priority

### 1. TypedDict response types on all server tools
**File:** `src/apple_mail_mcp/server.py` — every tool handler  
**Problem:** All 14 tools return `dict[str, Any]`, giving callers no type safety and no IDE autocomplete on response keys. Success and error paths return different shapes with no contract enforcing it.  
**Fix:** Define `TypedDict` classes for each tool's success and error response, update return type annotations.  
**Prerequisite:** Write tests that validate response shapes before changing the types (TDD).

### 2. Magic constants scattered across files
**Files:** `src/apple_mail_mcp/security.py`, `src/apple_mail_mcp/server.py`  
**Problem:** Rate limits (`window_seconds=60`, `max_operations=10`), bulk limits (`max_items=100`), and size limits (`25 * 1024 * 1024`) are hardcoded inline at multiple call sites. Changing a limit requires hunting across files.  
**Fix:** Centralise in a `config.py` (or constants block in `security.py`) and reference from all call sites.  
**Prerequisite:** None — safe standalone change.

### 3. Global mutable singletons
**Files:** `src/apple_mail_mcp/server.py:34-37`, `src/apple_mail_mcp/security.py:115-116`  
**Problem:** `mail = AppleMailConnector()`, `mcp = FastMCP(...)`, `operation_logger`, and `rate_limiter` are module-level globals. Makes unit testing without `@patch` surgery difficult and rate limiter state bleeds between test runs.  
**Fix:** Investigate whether FastMCP supports dependency injection. At minimum, expose a factory function so tests can instantiate with mock connectors.  
**Prerequisite:** Research FastMCP's tool registration model first — this may be a framework constraint.

---

## Moderate Priority

### 4. Path traversal check order in `save_attachments`
**File:** `src/apple_mail_mcp/mail_connector.py` — `save_attachments()`  
**Problem:** The `..` check runs before `resolve()`, so symlink-based path escapes are not caught. The check should validate the resolved path against an allowed base directory.  
**Fix:**
```python
def validate_safe_directory(path: Path, allowed_base: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(allowed_base.resolve())  # raises ValueError if outside
    return resolved
```
**Prerequisite:** Integration test covering symlink traversal attempt.

### 5. `"ruwi"` hardcoded in generic security module
**File:** `src/apple_mail_mcp/security.py:310-312`  
**Problem:** Prompt injection patterns reference `"ruwi"` by name. This is a domain-specific name inside a published general-purpose MCP library.  
**Fix:** Move domain-specific patterns to project-level config (e.g. `CLAUDE.md` or a settings file); keep only universally applicable patterns in `security.py`.  
**Prerequisite:** None.

### 6. `permanent` delete — both branches produce identical AppleScript
**File:** `src/apple_mail_mcp/mail_connector.py` — `delete_messages()`  
**Problem:** `permanent=True` and `permanent=False` generate identical AppleScript (`delete msg`). In Apple Mail's AppleScript, `delete` always moves to Trash — there is no permanent delete via this path. The `permanent` parameter has no effect.  
**Fix:** Research the correct AppleScript for permanent deletion (likely requires emptying trash or using a different verb). Update or remove the `permanent` parameter.  
**Prerequisite:** Integration test verifying both delete behaviours before changing AppleScript.

---

## Low Priority

### 7. `list_accounts` has no `@mcp.tool()` wrapper
**File:** `src/apple_mail_mcp/server.py`  
**Problem:** `list_accounts` exists on `AppleMailConnector` but is not exposed as an MCP tool. Flagged by `check_client_server_parity.sh` on every run.  
**Fix:** Either add a `list_accounts` tool to `server.py`, or explicitly document it as an internal-only method and update the parity script to exclude it.  
**Prerequisite:** None.

### 8. `send_email_with_attachments` complexity approaching threshold
**File:** `src/apple_mail_mcp/server.py:405`  
**Problem:** CC=17, threshold is 20. Not over the limit but the function handles rate limiting, recipient validation, file existence checks, confirmation, and sending — doing too many things.  
**Fix:** Extract validation steps into a `_validate_attachments_request()` helper.  
**Prerequisite:** None — refactor only, no behaviour change.

---

## Completed (April 2026)

| Item | Details |
|------|---------|
| Deferred imports → top-level | All intra-package imports moved to module top in `mail_connector.py`, `server.py`, `utils.py`, `security.py` |
| `_run_applescript` catch-all removed | Broad `except Exception` that swallowed programming errors removed |
| Duplicate recipient list pattern | `format_recipient_list()` extracted to `utils.py`; used in `send_email`, `send_email_with_attachments`, `save_draft` |
| Flag color map bug | `"red"` was mapped to `0` (same as `"none"`); fixed to `1` |
| `sanitize_message_id` consistency | `get_message`, `get_attachments`, `save_attachments` now use `sanitize_message_id` instead of `escape_applescript_string(sanitize_input(...))` |
| `Callable` import modernised | Updated to `collections.abc.Callable` |
| Unused imports cleaned up | `MailOperationCancelledError`, unused `result =` assignments, test file cruft |
| Complexity script broken | `radon` invoked via `uv run radon` after install so it resolves from the virtualenv |
