---
name: Never send emails — save_draft only
description: Never use reply_to_message or send_email for Ruwi's Cakes workflow — these send immediately. Always use save_draft.
type: feedback
originSessionId: 458bedd0-541e-4fd7-a08a-c2bad9bc3d4d
---
Never use `reply_to_message` or `send_email` when processing Ruwi's Cakes emails. Both tools send emails immediately. The only permitted tool for outgoing messages is `save_draft`.

**Why:** The workflow rule is "NEVER send emails — save as drafts only" (stated in both CLAUDE.md and morning-email.md). The owner reviews and sends drafts manually. Using reply_to_message bypasses this review step entirely.

**How to apply:** When the ToolSearch returns reply_to_message or send_email alongside save_draft, do not call them. Compose all outgoing content using save_draft only, addressed to the recipient's email address. Do not load reply_to_message via ToolSearch at all — it serves no safe purpose in this workflow.
