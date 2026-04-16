Run the end-of-session wrap-up to make sure everything is committed and pushed.

## Steps

1. Run `git status` to check for uncommitted changes
2. Run `git log --oneline origin/main..HEAD` to check for unpushed commits
3. If there are **uncommitted changes**:
   a. Run `git diff` to understand what changed
   b. Stage the relevant modified files (do not use `git add -A` — add files by name)
   c. Write a concise commit message summarising the changes
   d. Commit and push to origin/main
4. If there are **unpushed commits** (but no uncommitted changes), push to origin/main
5. If already clean and up to date, confirm
6. Report the final state — last 3 commits and confirmation the branch is up to date with origin
