# Eval changelog

How Foreman's extraction improved, and why. Each entry records a failure seen
on the eval set, its root cause, the change made, and the result.

Cause types: **code** (bug in our code), **prompt** (unclear instructions to the
model), **key** (the answer key itself was wrong).

---

## 2026-10-11: Items not assigned to a project

_(Gemini 3.8 Flash, checked by hand on case_01 before the eval script existed)_

- **Seen in:** case_01. Both items had project `None`.
- **Cause:** code. The prompt listed project codes and names but not clients.
  The email only names the client contact (Dana, Millbrook Public Works),
  so the model had no way to link it to Riverside.
- **Change:** include each project's client name and email in the prompt.
- **Result:** case_01 items now assigned to RVS-2041.

## 2026-10-11: Addressee treated as owner

- **Seen in:** case_01. Owner set to "Sam" because the email opened with "Hi Sam".
- **Cause:** prompt. The rule "owner only if the document names who will do it"
  was too general; the model counted a greeting as naming someone.
- **Change:** added rule: the person a message is addressed to is not the owner
  unless the document says they will do it.
- **Result:** case_01 owners now null on both items.

## 2026-10-11: Answer key split one request into two

- **Seen in:** case_01. Foreman found 2 items; the key had 3.
- **Cause:** key. The key listed "add a 100-year storm check" and "tell the client
  whether it affects the schedule" as separate requests. Rereading the email, the
  client only asked a question; she did not ask for the check to be done.
- **Change:** merged into one request in the key. Added the rule "a question about
  whether something can be done is one request" to LABELING.md and the prompt.
- **Result:** case_01 now matches the key: 2 of 2 items.

## 2026-10-11: Eval run hit free-tier quota

- **Seen in:** first full eval run crashed partway with a 429 error.
- **Cause:** code / infrastructure. The Gemini free tier allows 20 requests per day
  per model; one eval run needs about 30. A single failed judge call also crashed
  the whole run.
- **Change:** switched to OpenAI gpt-5-mini on a paid key (separate OpenAI project
  for cost tracking). The provider swap required only two lines in .env. The eval
  now records a failed judge call as a problem on that case and continues.
- **Result:** full runs complete; all entries below use gpt-5-mini.

## 2026-10-11: Baseline (gpt-5-mini)

- **Precision 0.68, recall 0.86** (19 of 28 found correct; 19 of 22 expected found).
- Main issues: background facts reported as items (4), one sentence extracted
  twice (2), a role used as owner (1), request vs deadline confusion (1),
  project not assigned when the email only names the client by first name (1).

## 2026-10-11: Round 1 — noise rules and filed-under project

- **Cause:** prompt (4 new rules: no background facts, extract each item once,
  owner must be a person, date-only changes are deadlines) and code (pass the
  project the document was filed under, as a real inbox would know the sender).
- **Result:** precision 0.68 → 0.83, recall 0.86 → 0.86. Extras 9 → 4.
- **Remaining:** one failure was the judge's error, not the model's (case_02:
  "Marcus Reed" vs "the County"); the addressee-as-owner bug returned after
  switching from Gemini to gpt-5-mini, so prompt fixes don't always transfer
  between models.

## 2026-10-11: Round 2 — judge context and stricter rules

- **Cause:** eval tooling (the judge saw only summaries, so it could not tell that
  "Marcus Reed" works for "the County") and prompt (stronger owner rule, broader
  background-facts rule).
- **Change:** the judge now sees each item's type, owner and due date, plus the
  source document. Owner and background-facts rules rewritten.
- **Result:** precision 0.83 → 0.79, recall 0.86 → 0.86. Targeted fixes worked
  (case_01 owner, case_02 pairing, case_13 tip). But the new owner rule ("the person
  being asked is never the owner") contradicted the key on case_12 ("Could Casey
  add..."), and four other cases flipped between runs with no related change.
- **Lesson:** with 22 items, one item is ~4 points of precision, so single-run
  differences are within noise. From here: fix only clear bugs, and compare
  across repeated runs.

## 2026-10-11: Measuring run-to-run variance

- Fixed the case_12 conflict (owner rule now separates "named as the doer" from
  "greeted"), then ran the same code and prompt twice: precision 0.80 / 0.75,
  recall 0.91 / 0.82.
- Scores swing 5-9 points with no changes, so single-run comparisons are unreliable
  at this eval size. Round 2's precision "drop" (0.83 → 0.79) was within noise.
- Consistent failures (both runs): case_04 RFI split into three items; case_02
  "on track" date reported as an item. Intermittent: owner taken from the greeting
  (different cases each run), case_03 date.
- Decision: replace the owner prompt rule with a code check, since two rounds of
  prompt rules only fixed it some of the time.

## 2026-10-11: Round 3 — a rule that made things worse

- **Change:** added an owner code check (the owner's name must appear in the
  quoted evidence), a prompt rule that the quote must include the owner's name,
  and a rule that a request and its response date are one item.
- **Result:** precision 0.82 / 0.85, recall 0.64 / 0.77 (two runs). Recall dropped.
- **Cause:** the "quote must include the name" rule made the model rewrite quotes
  instead of copying them; the quote check correctly dropped those items (cases 02,
  03, 09). It also stretched quotes to include greetings ("Hi Sam"), which let
  addressee owners slip past the new code check.
- **What worked:** the RFI rule fixed case_04 in both runs. The quote check blocked
  fabricated evidence rather than letting it through.
- **Next:** reverted the quote-must-include-name rule; kept the RFI rule and the
  owner check.

## 2026-10-11: Round 4 — reverted the bad rule

- **Change:** removed the "quote must include the owner's name" rule. Kept the
  owner code check and the RFI rule.
- **Result:** precision 0.86 / 0.90, recall 0.86 / 0.82 (two runs). Owner taken
  from a greeting is fixed in both runs; the code check works once quotes are
  copied naturally.
- **Day summary:** precision 0.68 → ~0.88, recall ~0.86 → ~0.84 (within noise).
- **Known remaining (consistent across runs):** case_02 "on track" date reported
  as an item; case_03 park and new date merged into one item; case_10 date-only
  change labeled request instead of deadline. Deferred until the eval set grows
  to 30 cases, so changes can be measured reliably.
