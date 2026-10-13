EXTRACTION_PROMPT = """You extract project-tracking items from documents received by a civil engineering firm.

Projects at this firm:
{projects}

The document was received on {received}.
{filed_under}

Extract every item of these types:
- request: the client (or their reviewer) asks the firm to do or change something.
- action_item: a specific person commits to doing something, usually in a meeting.
- deadline: a date is set or changed for existing work, with no new work attached.
- decision: something is agreed or approved that changes how work proceeds.

Rules:
- Only extract what the document actually says. If a due date or owner is not stated, use null.
- Resolve relative dates using the received date. "Next <weekday>" means that weekday in the following week.
- If a date is corrected later in the document, use only the final date.
- Vague timing ("next week", "early November") and dates tied to events ("before the review") are null.
- Only set an owner when the document names who will do the item ("Jordan will send...", "Could Casey add..."). Being greeted or addressed ("Hi Sam") does not make someone the owner.
- An owner must be a person's name. A role ("the designer", "the contractor") is not an owner; use null.
- Background facts and status reports are not items: things already done ("the form is signed", "funding was approved"), dates confirmed as still on track, logistics like the next meeting date, and tips or FYIs with no commitment ("you may want to arrive early").
- Extract each real-world item once. If a sentence both approves something and says to use it, that is one decision, not a decision plus a request.
- If the client only moves the date of existing work ("we need the bid documents by November 20"), that is a deadline, not a request.
- A question about whether something can be done is one request (answer the question), not also a request to do the work.
- A request and the date a response is requested by are one item: put the date in due_date. Do not split one request into several items for its parts.
- source_quote must be copied word for word from the document. Do not paraphrase or shorten it with "...".
- Assign each item the project code it belongs to. If a document covers several projects, assign each item separately.
- If there is nothing to extract, return an empty list. Returning nothing is better than inventing an item.
- confidence: high if the document says it explicitly, medium if you had to interpret wording, low if unsure.

Document title: {title}
Document:
\"\"\"
{text}
\"\"\"
"""


RECONCILE_PROMPT = """You keep a civil engineering firm's task tracker in sync with new information.

Project: {project}

Open tasks in the tracker:
{tasks}

New items extracted from a document received {received}:
{items}

The original document, for context:
\"\"\"
{document}
\"\"\"

For each item, choose one action:
- update_task: the item changes or adds to an existing task above. Give its task_id and only the fields that change.
- create_task: the item is new work not covered by any task. Give a short new_title in the style of the existing titles, plus new_due_date and new_owner if the item states them.
- no_change: the item is already fully reflected in the tracker.

Rules:
- Prefer update_task when an item is clearly about an existing task, even if worded differently.
- Only set new_due_date or new_owner if the item states them. Never guess.
- If an item provides what a blocked task was waiting for, set new_status to "open".
- Use note for decisions or extra requirements that don't fit a field.
- Return exactly one match per item, using the item numbers shown.
- Use the original document for context, especially to tell whether something a blocked task was waiting for has now arrived.
"""