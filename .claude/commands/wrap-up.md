Run the end-of-session wrap-up to make sure everything is committed and pushed.

## Steps

1. **Check for changes** — run `git status` and `git log --oneline origin/main..HEAD` to see what's uncommitted or unpushed.

2. **If there are uncommitted changes**:
   a. Run `git diff` to understand what changed
   b. Stage the relevant files by name (do not use `git add -A`)
   c. Write a concise commit message summarising the changes
   d. Commit and push to origin/main

3. **If there are only unpushed commits**, push to origin/main.

4. **If already clean and up to date**, confirm.

5. **Check docs are in sync** — compare the current state of the codebase against these docs and update any that are stale:
   - `.claude/CLAUDE.md` — tool count, unit test count
   - `docs/reference/TOOLS.md` — every public `@mcp.tool()` in `server.py` must have a reference entry
   - `docs/reference/ARCHITECTURE.md` — tool count in the component diagram
   - `TECH_DEBT.md` — tool count references; remove any items that were resolved this session
   - `README.md` — feature list or tool count if present
   - If anything is stale, update and commit in a separate "Update docs" commit before reporting done.

6. **Report** the final state — last 3 commits and confirmation the branch is up to date with origin.

7. **Back up Claude data to iCloud** — sync `~/.claude/` to iCloud Drive:
   ```bash
   rsync -a --delete ~/.claude/ ~/Library/Mobile\ Documents/com~apple~CloudDocs/claude-config/
   ```
   This backs up memory files, session history, settings, and all Claude data. Report how many files were synced.

6. **Back up Claude data to iCloud** — sync `~/.claude/` to iCloud Drive:
   ```bash
   rsync -a --delete ~/.claude/ ~/Library/Mobile\ Documents/com~apple~CloudDocs/claude-config/
   ```
   This backs up memory files, session history, settings, and all Claude data. Report how many files were synced.

## Note
Memory files (`.claude/memory/`) are excluded from git — the repo is public. Memory stays local only. The iCloud backup (step 6) is where they are kept safe.
