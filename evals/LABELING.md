# Labeling rules

Each extracted item is exactly one of these types:

- **request**: the client (or their reviewer) asks the firm to do or change something.
- **action_item**: a specific person commits to doing something, usually in a meeting.
- **deadline**: a date is set or changed for existing work, with no new work attached.
- **decision**: something is agreed or approved that changes how work proceeds.

Rules:

- Only extract what the document actually says. If a due date or owner is not stated, it is null.
- Relative dates ("by Friday") are resolved using the document's received date.
- If a date is corrected later in the same document, only the final date counts.
- Status updates with nothing new ("still on track") are not items.
- Each item has a `match` field for reconciliation: `new`, or `update: <existing task title>`
  when it changes or relates to an existing task.
