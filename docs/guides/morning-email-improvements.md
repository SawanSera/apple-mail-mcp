# Morning Email Workflow — Improvements & Known Issues

Tracks potential improvements, known gaps, and proposed fixes for the `/morning-email` skill.
Add new items as they're discovered during runs. Reference this before modifying the skill.

---

## Performance

### P1 — Batch size guard before `get_messages_batch`

**Problem:** On heavy-volume days (this run: 46 emails), attempting a single batch fetch hits the 60-second default timeout and returns nothing — wasting a full minute before the retry split.

**Fix:** Before calling `get_messages_batch`, chunk the ID list into groups of ≤15 when there are more than 20 IDs. Never attempt a single call with more than 20 full-body fetches.

**Impact:** Saves ~60–75s on heavy days (timeout failure + retry overhead).

---

### P2 — Remove flag-color lookup calls

**Problem:** After finding flagged emails, the workflow makes individual `get_message` calls to determine flag color. The API always returns `flag_color: null` — the field is never populated. These calls return no useful information.

**Fix:** Remove the flag-color lookup step entirely. Treat `flagged: true` as owner-flagged and proceed directly to drafting. Flag color cannot be determined via the API.

**Impact:** Saves ~20–25s (5 × individual AppleScript calls).

---

### P3 — Fetch Sent folder in parallel with first inbox batch

**Problem:** The Sent folder search and batch fetch happen after the inbox batches complete, adding sequential latency.

**Fix:** Fire `search_messages` on the Sent folder in the same tool call as the first inbox `get_messages_batch`. Cache results and reuse throughout the run.

**Impact:** Saves ~15–20s on most days.

---

### P4 — Parallel sub-agents for order checks on heavy days

**Problem:** On days with 20+ orders, checking all orders sequentially in a single context window is the dominant cost (~15 min of model thinking for 29 orders × 7 checks).

**Fix:** When the inbox contains >15 WooCommerce orders, split into 2–3 parallel sub-agents, each receiving a subset of order JSON and returning structured findings. Coordinate results before ClickUp push.

**Impact:** Could reduce order-review phase from ~15 min to ~5 min on heavy days. Adds coordination overhead — only worth it above ~15 orders.

---

### P5 — Cache Sent folder patterns between runs

**Problem:** The Sent folder is re-fetched every run to understand response patterns (delivery zone replies, custom design responses, etc.). Most of these patterns are stable day-to-day.

**Fix:** Maintain a `memory/sent_patterns.md` file summarising the owner's standard responses by category (delivery zone denials, FAQ templates, design change confirmations). Update weekly. Skip the Sent batch fetch on days where no novel enquiry types appear.

**Impact:** Saves ~20–30s per run once the cache is warm. Risk: patterns go stale if owner's approach changes.

---

## Order Check Accuracy

### A1 — Hybrid compact/full-quote format for order checks

**Problem:** Pure narrative checking for all 29 orders generates excessive tokens. Pure compact checking risks missing judgment-intensive checks.

**Proposed format:** Use compact one-line output for the five mechanical checks, but always use full-quote for the two prose-dependent checks and the cross-field check:

```
#37702 Camilla | date:25/04✓ | flavour✓ | addr✓ | phone✓
  → NOTES (verbatim): "If possible, a morning delivery would be appreciated" → ⚠ delivery window
  → TOPPER: selection="Happy Birthday", custom_msg_field=empty → ✓
```

**Rules for compact fields:**
- `date:` — must quote the explicit `Delivery Date:` field value, never the order-date in brackets. Flag if absent or if date ≤ today.
- `flavour:` — present/absent
- `addr:` — flag if street number, street name, or suburb missing
- `phone:` — flag if not matching `04xxxxxxxx` or `+614xxxxxxxx`

**Rules for full-quote fields (never just ✓):**
- Notes field: always quote verbatim — required for delivery window (check 2) and design change (check 7)
- Topper: always state both the topper selection value AND whether the custom message field is populated — required for mismatch detection (check 4)

**Impact:** ~8–12 min saved on a 29-order day with no accuracy loss on the reliable checks.

---

### A2 — Delivery date threshold should be "today or earlier", not "before today"

**Problem:** The current check flags delivery dates *before* today. An order placed overnight for delivery *today* passes the check — but by morning the cake may already be in production with an error that can't be fixed.

**Fix:** Change the threshold to `≤ today` (today or earlier) rather than `< today`.

**Skill change:** Update check 1 in the `morning-email` skill:
> *"If the delivery date is **today or earlier**, flag as 'Delivery date is today or in the past.'"*

---

### A3 — Distinguish year-typo past dates from missing-field past dates

**Problem:** The current flag description is always "Delivery date is in the past — possible website error." A date 12+ months in the past is likely a year typo by the customer (e.g., 2025 instead of 2026), not a website field error — and needs more urgent customer contact.

**Fix:** Add a secondary condition:
> *"If the past delivery date is more than 30 days ago, append 'possible year or month typo — contact customer to confirm' to the flag description."*

---

### A4 — Non-standard order structures (Standard Cake product)

**Problem:** The "Standard Cake" product uses a different email layout — flavour, size, design, and toppings are itemised as separate line items rather than a single `Select your flavour:` field. A compact or mechanical flavour-present check may either false-positive or false-negative on these orders.

**Fix:** Add an explicit note to the order check instructions:
> *"For 'Standard Cake' products, the flavour field appears under the 'Flavours :' line item, not 'Select your flavour:'. Check both field names."*

**Examples seen:** Orders #37661 (Cyril Paiva), #37691 (Y-Nhi Le-Pham).

---

## Skill / Prompt Gaps

### S1 — Failed payment notifications are not auto-skipped but need no action

**Problem:** `[Ruwi's Cakes]: Order #XXXXX has failed` emails arrive from `order@ruwiscakes.com.au`. They don't match the WooCommerce new-order pattern (`New order #`) so they fall through to the general processing queue. They are purely informational system notifications.

**Fix:** Add to the auto-skip rules:
> *"Subject matches `[Ruwi's Cakes]: Order # has failed` — skip silently, no tally."*

Or treat as a special informational category: note in the summary if a failed payment has no corresponding successful order for the same customer on the same day.

---

### S2 — FAQ emails from the same customer submitted twice

**Problem:** Website form submissions sometimes arrive as duplicates — same customer, same question, slightly different times (observed: Manon's baby shower enquiry arrived twice, 10 hours apart). The second submission has `replied_to: false` even though the owner already replied to the first. Drafting a second reply wastes time and creates a duplicate in the customer's inbox.

**Fix:** Before drafting for a FAQ email, check the Sent cache for a recent reply to the same customer email address. If a reply exists within the last 24 hours, skip drafting and note "already replied" in the summary.

---

### S3 — `replied_to: false` on "thank you" closure emails

**Problem:** Emails like "Life saver! Thank you!" have `replied_to: false` but clearly need no reply — the conversation is complete. The workflow currently relies on manually recognising these, which takes analysis time.

**Fix:** Add a heuristic to the customer email triage step:
> *"If the most recent customer message is clearly a closure (e.g., 'thank you', 'perfect', 'all good', 'sounds great', no question or request present), skip drafting and note 'conversation closed' in the summary."*

---

## Considered and Rejected

| Idea | Reason rejected |
|------|----------------|
| Pure compact format for all 7 order checks | Risks missing delivery window (check 2), design-in-Notes (check 7), and topper mismatch (check 4) — judgment calls that require reading prose, not just field-present checks |
| Pre-filtering orders by read status to reduce batch size | `read_status: true` only means the owner opened the email, not that it's been reviewed for issues — not a safe filter |
| Skip Sent fetch entirely and rely on model knowledge | Sent patterns change over time (pricing, collections, policies) — model knowledge goes stale |
