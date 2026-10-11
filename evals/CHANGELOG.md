# Eval changelog

How Foreman's extraction improved, and why. Each entry records a failure seen
on the eval set, its root cause, the change made, and the result.

Cause types: **code** (bug in our code), **prompt** (unclear instructions to the
model), **key** (the answer key itself was wrong).

---

## 2026-10-11: Items not assigned to a project

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

## 2026-10-11: Answer key split one request into two
- **Seen in:** case_01. Foreman found 2 items; the key had 3.
- **Cause:** key. The key listed "add a 100-year storm check" and "tell the client
  whether it affects the schedule" as separate requests. Rereading the email, the
  client only asked a question; she did not ask for the check to be done.
- **Change:** merged into one request in the key. Added the rule "a question about
  whether something can be done is one request" to LABELING.md and the prompt.
- **Result:** case_01 now matches the key: 2 of 2 items.