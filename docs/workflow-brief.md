# Workflow brief: Hollis & Grant Civil Engineers (fictional)

## The firm

A small civil engineering firm, about 25 people, doing municipal and
land-development work: drainage, roads, bridges, subdivisions. Two project
managers each run two projects, supported by engineers, a surveyor, and a
permitting specialist.

## How project coordination works today

- Client requests arrive by email, in meetings, and as formal RFIs
  (requests for information).
- Each PM keeps a task tracker per project.
- After each meeting or important email, the PM is supposed to update the
  tracker by hand.
- Every two weeks, the PM writes a status update email to each client.

## What goes wrong

- Requests buried in email threads never make it into the tracker.
- A client changes a date in a reply, and the tracker keeps the old one.
- Writing a status update takes 1-2 hours per project, because the PM
  re-reads everything.
- Work gets blocked waiting on the client (a signed form, data from their
  consultant), but nobody tracks what is being waited on.

## What Foreman does

1. Reads each new email, meeting note, or RFI.
2. Pulls out requests, action items, deadlines, and decisions, quoting the
   source.
3. Compares them with the tracker: new task, update, or conflict.
4. Proposes changes for the PM to approve. Nothing changes without approval.
5. Answers "what's outstanding?" and drafts the client update with citations.

## What Foreman does not do

- Send anything to a client on its own
- Guess missing dates or owners
- Make engineering decisions

## Success looks like

- Every client request ends up in the tracker or is deliberately rejected
- Status update prep drops from hours to minutes
- PMs trust it: high precision on extracted items, measured by evals
