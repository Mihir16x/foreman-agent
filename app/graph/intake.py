from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.db import connect
from app.extract import ExtractionFailed, extract_items
from app.reconcile import reconcile
from app.tools import save_extracted_items


class IntakeState(TypedDict, total=False):
    """Everything the steps share. Each step reads what it needs and adds its results."""
    document_id: int
    document: dict
    projects: list[dict]
    items: list[dict]
    proposals: list[dict]
    skipped: list[dict]
    status: str
    error: str


# ---------- Steps ----------

def load_document(state: IntakeState) -> dict:
    with connect() as conn:
        document = conn.execute(
            """
            select d.id, d.title, d.raw_text, d.received_at::date as received,
                   p.code as project_code
            from documents d left join projects p on p.id = d.project_id
            where d.id = %s
            """,
            (state["document_id"],),
        ).fetchone()
        projects = conn.execute(
            "select id, code, name, client_name, client_email from projects order by code"
        ).fetchall()
    if document is None:
        return {"error": "document not found"}
    return {"document": document, "projects": projects}


def extract(state: IntakeState) -> dict:
    doc = state["document"]
    try:
        kept, dropped = extract_items(doc["title"], doc["raw_text"], doc["received"],
                                      state["projects"], doc["project_code"])
    except ExtractionFailed as e:
        return {"error": str(e)}

    item_ids = save_extracted_items(doc["id"], kept)
    items = [
        {"id": item_id, "type": it.type, "summary": it.summary, "due_date": it.due_date,
         "owner": it.owner, "project_code": it.project_code}
        for item_id, it in zip(item_ids, kept)
    ]
    skipped = [{"item": d.summary, "why": "dropped: quote not found in document"} for d in dropped]
    return {"items": items, "skipped": skipped}


def reconcile_items(state: IntakeState) -> dict:
    doc = state["document"]
    projects_by_code = {p["code"]: p for p in state["projects"]}
    proposals, skipped = [], list(state.get("skipped", []))

    for item in state["items"]:
        if item["project_code"] is None:
            skipped.append({"item": item["summary"], "why": "no project assigned"})
        elif item["project_code"] not in projects_by_code:
            # Don't trust the model: a project code that doesn't exist is an error, not a project.
            skipped.append({"item": item["summary"], "why": f"unknown project {item['project_code']}"})

    codes = sorted({i["project_code"] for i in state["items"] if i["project_code"] in projects_by_code})
    for code in codes:
        project_items = [i for i in state["items"] if i["project_code"] == code]
        try:
            saved, project_skipped = reconcile(projects_by_code[code], project_items,
                                               doc["received"], doc["raw_text"])
        except Exception as e:
            return {"proposals": proposals, "skipped": skipped,
                    "error": f"reconcile failed for {code}: {type(e).__name__}"}
        proposals += [{"id": proposal_id, **p} for proposal_id, p in saved]
        skipped += project_skipped

    return {"proposals": proposals, "skipped": skipped}


def finish(state: IntakeState) -> dict:
    dropped = [s for s in state.get("skipped", []) if s["why"].startswith("dropped")]

    if state.get("error"):
        status = "needs_manual_review"
    elif not state.get("items"):
        # If the quote check threw items away, something was found: a human should look.
        status = "needs_manual_review" if dropped else "no_items"
    elif state.get("proposals"):
        status = "proposed"
    else:
        status = "no_changes"

    if state.get("document"):
        with connect() as conn:
            conn.execute("update documents set intake_status = %s where id = %s",
                         (status, state["document"]["id"]))
    return {"status": status}

# ---------- Routing: which step comes next ----------

def after_load(state: IntakeState) -> str:
    return "finish" if state.get("error") else "extract"


def after_extract(state: IntakeState) -> str:
    return "reconcile" if state.get("items") and not state.get("error") else "finish"


# ---------- Wire it together ----------

def build_intake_graph():
    graph = StateGraph(IntakeState)
    graph.add_node("load_document", load_document)
    graph.add_node("extract", extract)
    graph.add_node("reconcile", reconcile_items)
    graph.add_node("finish", finish)

    graph.add_edge(START, "load_document")
    graph.add_conditional_edges("load_document", after_load, ["extract", "finish"])
    graph.add_conditional_edges("extract", after_extract, ["reconcile", "finish"])
    graph.add_edge("reconcile", "finish")
    graph.add_edge("finish", END)
    return graph.compile()


intake_graph = build_intake_graph()