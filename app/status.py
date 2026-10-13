from datetime import date

from app.extract import get_llm
from app.models import CitedParagraph, StatusDraft
from app.prompts import STATUS_PROMPT
from app.tools import find_project, get_open_tasks, get_recent_items, propose_change

from app.db import connect


class ProjectNotResolved(Exception):
    """Zero or several projects match the name. Carries the matches so the caller can ask."""


def resolve_project(name: str) -> dict:
    matches = find_project(name)
    if len(matches) != 1:
        raise ProjectNotResolved(matches)  # never guess between projects
    return matches[0]


def gather_facts(project: dict) -> dict[str, str]:
    """Every fact the model may use, keyed by a citation id: T<task id> or I<item id>."""
    facts = {}
    for t in get_open_tasks(project["id"]):
        line = f"Task: {t['title']} | owner: {t['owner']} | due: {t['due_date']} | status: {t['status']}"
        if t["blocked_reason"]:
            line += f" | blocked because: {t['blocked_reason']}"
        if t["notes"]:
            line += f" | notes: {t['notes']}"
        facts[f"T{t['id']}"] = line
    for i in get_recent_items(project["id"]):
        facts[f"I{i['id']}"] = (
            f"Client {i['type']} from '{i['document']}' ({i['received']}): "
            f"{i['summary']} | due: {i['due_date']}"
        )
    return facts


def check_citations(paragraphs: list[CitedParagraph], facts: dict) -> list[str]:
    """Paragraphs with no citation, or citing an id that doesn't exist, are unsupported."""
    return [
        p.text for p in paragraphs
        if not p.citations or any(c not in facts for c in p.citations)
    ]




def pending_reviews(project_id: int) -> int:
    """Tracker changes for this project that are still waiting for a decision."""
    with connect() as conn:
        return conn.execute(
            """
            select count(*) as n from proposed_changes
            where project_id = %s and status = 'pending' and kind <> 'client_update'
            """,
            (project_id,),
        ).fetchone()["n"]


def draft_status_update(project_name: str, propose: bool = True) -> dict:
    project = resolve_project(project_name)
    facts = gather_facts(project)

    prompt = STATUS_PROMPT.format(
        project=f"{project['code']}: {project['name']}",
        client=project["client_name"],
        today=date.today(),
        facts="\n".join(f"[{fid}] {text}" for fid, text in facts.items()) or "(no facts)",
    )
    draft = get_llm().with_structured_output(StatusDraft).invoke(prompt)
    if draft is None:
        raise RuntimeError("model returned no draft")

    unsupported = check_citations(draft.outstanding + draft.email_paragraphs, facts)

    # Greeting and sign-off come from code, not the model
    parts = [f"Hello {project['client_name']} team,"]
    parts += [p.text for p in draft.email_paragraphs]
    if draft.questions_for_client:
        parts.append("Open questions for you:\n" + "\n".join(f"- {q}" for q in draft.questions_for_client))
    parts.append("Best regards,\nHollis & Grant Civil Engineers")
    body = "\n\n".join(parts)

    cited = sorted({c for p in draft.email_paragraphs for c in p.citations if c in facts})
    result = {
        "project": f"{project['code']}: {project['name']}",
        "outstanding": draft.outstanding,
        "subject": draft.email_subject,
        "body": body,
        "unsupported": unsupported,
        "proposal_id": None,
        "pending_reviews": pending_reviews(project["id"]),
    }

    if propose:
        result["proposal_id"] = propose_change(
            project["id"], "client_update",
            {"subject": draft.email_subject, "body": body,
             "citations": cited, "unsupported": unsupported},
            "Drafted client status update",
            [int(c[1:]) for c in cited if c.startswith("I")],
        )
    return result