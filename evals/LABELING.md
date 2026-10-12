# Labeling rules

Each extracted item is exactly one of these types:

- **request**: the client (or their reviewer) asks the firm to do or change something.
- **action_item**: a specific person commits to doing something, usually in a meeting.
- **deadline**: a date is set or changed for existing work, with no new work attached.
- **decision**: something is agreed or approved that changes how work proceeds.

Rules:

- Only extract what the document actually says. If a due date or owner is not stated, it is null.
- Relative dates ("by Friday") are resolved using the document's received date.
- "Next <weekday>" means that weekday in the following week (sent Tuesday Oct 6, "next Friday" = Oct 16).
- If a date is corrected later in the same document, only the final date counts.
- Vague timing ("next week", "early November") and dates tied to events ("before the 30% review") are null.
- Only set an owner when the document names who will do the item ("Jordan will send...", "Could Casey add..."). Being greeted or addressed ("Hi Sam") does not make someone the owner.
  The person a message is addressed to, or the person being asked, is never the owner.
- An owner must be a person's name. A role ("the designer", "the contractor") is not an owner; use null.
- Background facts and status reports are not items: things already done ("the form is signed",
  "funding was approved"), dates confirmed as still on track, logistics like the next meeting date,
  and tips or FYIs with no commitment ("you may want to arrive early").
- Extract each real-world item once. If a sentence both approves something and says to use it,
  that is one decision, not a decision plus a request.
- If the client only moves the date of existing work ("we need the bid documents by November 20"),
  that is a deadline, not a request.
- A question about whether something can be done is one request (answer the question),
  not also a request to do the work.
- Each item has a `match` field for reconciliation: `new`, or `update: <existing task title>`
  when it changes or relates to an existing task.
- A request and the date a response is requested by are one item: put the date in due_date. Do not split one request into several items for its parts.
