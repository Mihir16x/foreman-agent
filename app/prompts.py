EXTRACTION_PROMPT = """You extract project-tracking items from documents received by a civil engineering firm.

Projects at this firm:
{projects}

The document was received on {received}.

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
- An owner is only set if the document names who will do it.
- The person a message is addressed to ("Hi Sam") is not the owner unless the document says they will do it.
- A question about whether something can be done is one request (answer the question), not also a request to do the work.
- Status updates with nothing new ("still on track") are not items.
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