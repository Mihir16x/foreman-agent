# Changelog

How Foreman improved, and why. Each entry records a failure that was observed, its root
cause, the change made, and the measured result. Extraction changes are scored against the
eval set in `evals/cases/`; later sections cover reconciliation, the intake graph, approvals,
status updates, tests and the web app.

Cause types: **code** (bug in our code), **prompt** (unclear instructions to the model),
**key** (the answer key itself was wrong), **design** (a gap in how the steps fit together),
**eval tooling** (a bug in how we measure).

---

# Extraction

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
- **Also:** before that, `gemini-2.5-flash` returned 404 (retired for new accounts);
  switching to the current Flash model was a one-line change in .env.
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

## 2026-10-11: Eval script hid judge failures

- **Seen in:** code review of run_eval.py. The line that records a failed judge call
  was indented under `if error:`, so judge failures were only reported when
  extraction had also failed.
- **Cause:** eval tooling.
- **Change:** extraction and judge failures are each recorded on their own.
- **Lesson:** a bug in the measuring tool can make results look better than they
  are; the scorer gets the same review as the agent.

---

# Reconciliation

## 2026-10-13: No silent drops

- **Seen in:** case_01. 2 items extracted, 1 proposal; the permit item vanished.
- **Cause:** code. build_proposals skipped "no change" decisions and empty updates
  without recording them.
- **Change:** every item now ends up as a proposal or on a skipped list with a
  reason, including items the model forgot to decide on. Covered by a test.

## 2026-10-13: Context lost between pipeline steps

- **Seen in:** case_01. The permit task was proposed as "remains blocked pending
  the signed form", even though the email says the form is signed.
- **Cause:** design. Extraction correctly treats "the form is signed" as a
  background fact, not an item, so it never reached reconciliation, which only
  saw item summaries.
- **Change:** the reconciler now also receives the original document.
- **Result:** case_01 permit task now proposed as blocked → open, citing the signed form.
- **Known issue:** the 100-year schedule question alternates between a new task with
  its own due date (better: the date is trackable) and a note on the hydraulic model
  task. Deferred to a reconciliation eval using the `match` labels already in the
  answer keys.

---

# Intake graph

## 2026-10-13: First full inbox run

- Ran the LangGraph intake graph on all 15 documents. Every document ended with an
  explicit status (proposed, no_changes, no_items, needs_manual_review); no crashes.
  20 proposals created. case_06 correctly ended as no_items; case_05 produced
  proposals for two projects.

## 2026-10-13: "no_items" hid a dropped item

- **Seen in:** case_03 (Lot layout revisions) ended as no_items, but its only item
  had been dropped by the quote check (paraphrased quote).
- **Cause:** code. The finish step treated "no kept items" as "nothing found".
- **Change:** if the quote check dropped items and nothing else remains, the
  document is marked needs_manual_review.
- **Result:** on rerun the quote was copied correctly and case_03 produced a
  flag_conflict (lot layout Oct 13 → Oct 20). The new rule wasn't triggered on that
  run but is in place.

## 2026-10-13: Reconciliation matches on dates and events, not the work

- **Seen in:** driveway culvert survey request matched to "30% plan review meeting"
  (the email said "before the 30% review"); deck overlay question matched to "Prepare
  bid documents"; a draft erosion plan and the 100-year scenario merged into larger
  tasks, showing up as date conflicts.
- **Cause:** prompt. The model matches on dates and events mentioned rather than on
  what the work is; separate deliverables get merged into related tasks.
- **Decision:** deferred to a reconciliation eval in V2. Low risk meanwhile: nothing
  is applied without approval, and date changes are always flagged as conflicts.

## 2026-10-13: Reprocessing a document duplicates its results

- **Seen in:** rerunning document 3 created a second set of extracted items and a
  new proposal alongside the old ones.
- **Cause:** design. Intake isn't idempotent: it always adds, never replaces.
- **Decision:** known limitation for V1 (documents are normally read once). V2: before
  reprocessing, mark the document's earlier items and pending proposals as superseded.

---

# Approvals

## 2026-10-13: Approvals close the loop

- **Change:** approving a proposal now applies it to the tracker. The task change
  and the decision are saved in one transaction (all or nothing); a decided proposal
  can't be decided again; a proposal whose "from" values no longer match the task is
  refused as stale; only whitelisted task fields can change. 5 tests cover these rules.
- **Result:** on the real queue, approving #18 moved the bid date to Nov 20, #13
  unblocked the permit task, #1 (wrong task match) was rejected with a reason, and a
  second approval of #18 was refused.

## 2026-10-13: Background chatter leaking into task notes

- **Seen in:** proposal #20 (public meeting): the note included parking, AV and
  coffee details.
- **Cause:** design. A side effect of the context fix: the reconciler now sees the
  whole document, so it copies background details into notes, the same chatter
  extraction learned to ignore.
- **Decision:** harmless (a PM trims the note before approving); likely fix is a
  reconcile rule that notes describe the change only. Deferred to the V2
  reconciliation eval.

---

# Status updates

## 2026-10-13: Prompt syntax bug merged two prompts

- **Seen in:** adding STATUS_PROMPT. RECONCILE_PROMPT lost its closing triple quote,
  so Python read the next prompt as part of it.
- **Cause:** code (copy-paste error in a long string).
- **Change:** added tests/test_prompts.py, which fills every prompt with dummy values
  and fails in under a second on a missing quote or a mistyped placeholder.

## 2026-10-13: Status update drafted from a stale tracker

- **Seen in:** Riverside draft said the meeting is set for Nov 12 but will be
  scheduled "as planned (due Nov 5)".
- **Cause:** design. The Nov 5 → Nov 12 change (#20) was still pending review, so the
  tracker and the client's email disagreed and the model blended both.
- **Change:** drafting now warns, in code, when the project has proposals awaiting
  review: the tracker may be out of date.
- **Result:** the warning shows (5 pending); the meeting paragraph is now coherent.

## 2026-10-13: Internal jargon in the client email

- **Seen in:** "the public meeting task" and "RVS-2041" in the subject line.
- **Cause:** prompt. The rule only banned task ids.
- **Change:** rule now bans mentioning tasks, the tracker, or internal project codes.
- **Result:** next draft used plain language ("Riverside drainage update").

## 2026-10-13: Limitation of the citation check

- A paragraph can cite real fact ids and still describe them wrongly (the stale
  meeting paragraph passed the check). The check proves cited facts exist, not that
  the sentence is faithful to them. Remaining small inaccuracies (e.g. "as requested"
  for something the client only asked about) are left to human review, which every
  client update requires.

---

# Tests

## 2026-10-13: Fragile test depended on changing data

- **Seen in:** test_open_tasks_skip_done_but_include_blocked failed after approving
  #13, which unblocked the only blocked Riverside task.
- **Cause:** code (test design). The test relied on seed data the app is designed
  to change.
- **Change:** the test now creates its own blocked and done tasks and removes them
  afterwards (try/finally), like the review tests.

---

# Web app

## 2026-10-13: First live document through the UI

- Pasted a new email Foreman had never seen ("Could Casey have the culvert inlet
  survey done by October 23?"). Result: proposal #45, a new task with owner Casey,
  due Oct 23, the client's sentence shown as evidence, and the reason "separate
  deliverable needed for the 90% design".

## 2026-10-13: Duplicate pending proposals

- **Seen in:** #45 and #12 both propose creating the culvert inlet survey task
  (one from the design meeting, one from the client email).
- **Cause:** design. Reconciliation compares new items with the tracker, but not
  with proposals still waiting in the review queue.
- **Decision:** caught by review for now (approve #45, reject #12 as duplicate).
  V2: include pending proposals in reconciliation context, or flag likely
  duplicates in the review queue.

## 2026-10-13: Inbox status label was misleading after review

- **Seen in:** documents kept showing "Proposals waiting" after their proposals were
  approved; the label reflected intake time, not review progress.
- **Cause:** code (the label read only the document's intake status).
- **Change:** the label is now derived from the current status of the document's
  proposals: "3 to review", "Reviewed", "Needs a person to read it".
- **Result:** fixed in the UI redesign.

## 2026-10-13: UI readability

- **Seen in:** secondary text in light grey and italic evidence quotes were hard to
  read; the default red Approve button read as a warning; missing values ("Owner:
  none") looked like real data.
- **Change:** a drafting-sheet theme with darker secondary text, evidence in normal
  dark text with a rule, changes shown revision-style (old value struck through, new
  value bold), missing values shown as a muted "Not stated", green Approve, dates as
  "Oct 5, 2026". All client text is HTML-escaped before display.

---

# Scope decisions

- **No separate task-matching tool.** Projects have at most 7 open tasks, so the
  reconciler sees the whole list. A ranking step (trigram or embeddings) is worth
  adding only when projects have hundreds of tasks.
- **Streamlit instead of a FastAPI endpoint for approvals.** The UI calls the same
  tested `decide()` function directly; every safety rule lives in `app/`, so an API
  can be added later without changing them.