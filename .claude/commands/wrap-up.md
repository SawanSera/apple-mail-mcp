Run the end-of-session wrap-up to make sure everything is committed, pushed, docs are current, and data is backed up.

## Steps

1. **Check for changes** — run `git status` and `git log --oneline origin/main..HEAD` to see what's uncommitted or unpushed.

2. **If there are uncommitted changes**:
   a. Run `git diff` to understand what changed
   b. Stage the relevant files by name (do not use `git add -A`)
   c. Write a concise commit message summarising the changes
   d. Commit and push to origin/main

3. **If there are only unpushed commits**, push to origin/main.

4. **If already clean and up to date**, confirm.

5. **Check all markdown files are in sync** — run:
   ```bash
   find . -name "*.md" | grep -v ".venv\|__pycache__\|.pytest_cache\|node_modules"
   ```
   Read every file in the list and check whether its content reflects the current state of the codebase. Pay particular attention to:
   - **Tool counts** — any file mentioning a number of MCP tools (currently 16)
   - **Test counts** — any file mentioning unit/integration test counts
   - **API surface lists** — any file listing available tools or methods
   - **Architecture descriptions** — component diagrams, file line counts, module descriptions
   - **Tech debt items** — remove any items resolved this session
   - **Skill files** (`.claude/skills/*/SKILL.md`) — patterns, timings, or workarounds that changed
   - **Command files** (`.claude/commands/*.md`) — workflow steps that changed

   If anything is stale, update it and commit in a single "Update docs" commit before reporting done.

6. **Report** the final state — last 3 commits and confirmation the branch is up to date with origin.

7. **Back up Claude data to iCloud** — sync `~/.claude/` to iCloud Drive:
   ```bash
   rsync -a --delete ~/.claude/ ~/Library/Mobile\ Documents/com~apple~CloudDocs/claude-config/ && rsync -a --delete ~/.claude/ ~/Library/Mobile\ Documents/com~apple~CloudDocs/claude-config/ --stats 2>&1 | grep "Number of files"
   ```
   Report how many files were synced and confirm the backup completed successfully.

8. **Back up project to OneDrive** — sync the full project directory:
   ```bash
   rsync -a --delete \
     --exclude='.git/' \
     --exclude='__pycache__/' \
     --exclude='.venv/' \
     --exclude='.pytest_cache/' \
     --exclude='*.pyc' \
     --exclude='*.egg-info/' \
     /Users/sawanserasinghe/ClaudeWork/apple-mail-mcp/ \
     ~/Library/CloudStorage/OneDrive-Personal/Documents/Claude\ back\ up/ClaudeWork/apple-mail-mcp/ \
     --stats 2>&1 | grep "Number of files\|transferred\|deleted"
   ```
   Report files transferred and confirm the sync completed.

## Note
Memory files (`.claude/memory/`) are excluded from git — the repo is public. Memory stays local only. The iCloud backup (step 7) is where they are kept safe. The OneDrive backup (step 8) covers the full project including `.claude/commands/`, `scripts/`, and `docs/`.
