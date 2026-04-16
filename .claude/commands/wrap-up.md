Run the end-of-session wrap-up to make sure everything is committed and pushed.

## Steps

1. **Sync memory files** — copy all files from the Claude memory folder into the repo so they are git-backed:
   ```bash
   cp /Users/sawanserasinghe/.claude/projects/-Users-sawanserasinghe-ClaudeWork-apple-mail-mcp/memory/*.md .claude/memory/
   ```
   Create the `.claude/memory/` directory in the repo first if it doesn't exist.

2. **Check for changes** — run `git status` and `git log --oneline origin/main..HEAD` to see what's uncommitted or unpushed.

3. **If there are uncommitted changes** (including any updated memory or markdown files):
   a. Run `git diff` to understand what changed
   b. Stage the relevant files by name
   c. Write a concise commit message summarising the changes
   d. Commit and push to origin/main

4. **If there are only unpushed commits**, push to origin/main.

5. **If already clean and up to date**, confirm.

6. **Report** the final state — last 3 commits and confirmation the branch is up to date with origin.
