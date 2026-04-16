---
name: No subject prefix on drafts
description: Never add [CLAUDE DRAFT] or any prefix to draft email subject lines
type: feedback
originSessionId: 1ab1c700-8974-4e4d-ae99-379a61fb2117
---
Never add any prefix (e.g. "[CLAUDE DRAFT]") to draft email subject lines. Use the original subject exactly as-is.

**Why:** Owner preference — no tagging on subjects.

**How to apply:** When calling save_draft, pass the subject unchanged from the original email (e.g. "Re: Birthday Cake Order Request", not "[CLAUDE DRAFT] Re: Birthday Cake Order Request").
