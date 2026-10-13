import streamlit as st

from app.db import connect
from app.graph.intake import intake_graph
from app.review import ReviewError, decide
from app.status import draft_status_update

st.set_page_config(page_title="Foreman", layout="wide")

KIND_LABELS = {
    "create_task": "New task",
    "update_task": "Update",
    "flag_conflict": "Conflict",
    "client_update": "Client update",
}
STATUS_LABELS = {
    "new": "New",
    "proposed": "Proposals waiting",
    "no_changes": "No changes needed",
    "no_items": "Nothing to extract",
    "needs_manual_review": "Needs manual review",
}


def query(sql: str, params=()) -> list[dict]:
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def all_projects() -> list[dict]:
    return query("select id, code, name, client_name from projects order by code")


def flash(message: str) -> None:
    """Show a message after the page reloads."""
    st.session_state["flash"] = message
    st.rerun()


# ---------- Inbox ----------

def inbox_page():
    st.header("Inbox")
    st.caption("Client emails, meeting notes and RFIs. Foreman reads each one and proposes tracker changes.")

    with st.expander("Add a document"):
        projects = {"(not filed)": None} | {f"{p['code']}: {p['name']}": p["id"] for p in all_projects()}
        with st.form("add_document", clear_on_submit=True):
            project_label = st.selectbox("Project", list(projects))
            kind = st.selectbox("Kind", ["email", "meeting_note", "rfi", "report"])
            title = st.text_input("Title")
            text = st.text_area("Text", height=200)
            submitted = st.form_submit_button("Add and process")
        if submitted:
            if not title.strip() or not text.strip():
                st.error("Title and text are required.")
            else:
                with connect() as conn:
                    doc_id = conn.execute(
                        "insert into documents (project_id, kind, title, raw_text) "
                        "values (%s, %s, %s, %s) returning id",
                        (projects[project_label], kind, title, text),
                    ).fetchone()["id"]
                with st.spinner("Foreman is reading the document..."):
                    result = intake_graph.invoke({"document_id": doc_id})
                proposals = len(result.get("proposals", []))
                flash(f"'{title}': {STATUS_LABELS[result['status']]}, {proposals} proposals")

    new_ids = [r["id"] for r in query(
        "select id from documents where intake_status = 'new' order by received_at, id")]
    if new_ids and st.button(f"Process {len(new_ids)} new documents", type="primary"):
        progress = st.progress(0.0)
        for n, doc_id in enumerate(new_ids, 1):
            intake_graph.invoke({"document_id": doc_id})
            progress.progress(n / len(new_ids))
        flash(f"Processed {len(new_ids)} documents")

    documents = query(
        """
        select d.id, d.title, d.kind, d.received_at::date as received, d.intake_status,
               d.raw_text, p.code
        from documents d left join projects p on p.id = d.project_id
        order by d.received_at desc, d.id desc
        """
    )
    for d in documents:
        label = f"{STATUS_LABELS[d['intake_status']]}  ·  {d['title']}  ·  {d['code'] or 'not filed'}  ·  {d['received']}"
        with st.expander(label):
            st.text(d["raw_text"])
            items = query(
                "select type, summary, due_date, owner, source_quote "
                "from extracted_items where document_id = %s order by id",
                (d["id"],),
            )
            if items:
                st.markdown("**What Foreman extracted**")
                st.dataframe(items, hide_index=True)


# ---------- Review queue ----------

def review(proposal_id: int, decision: str, note: str) -> None:
    try:
        decide(proposal_id, decision, note or None)
    except ReviewError as e:
        st.error(f"#{proposal_id} not applied: {e}")
        return
    flash(f"#{proposal_id} {decision}")


def review_page():
    st.header("Review queue")
    st.caption("Nothing changes in the tracker until you approve it.")

    proposals = query(
        """
        select c.id, c.kind, c.payload, c.reason, c.cited_item_ids, p.code
        from proposed_changes c join projects p on p.id = c.project_id
        where c.status = 'pending'
        order by c.id
        """
    )
    if not proposals:
        st.success("All caught up. No proposals waiting.")
        return

    for r in proposals:
        payload = r["payload"]
        target = payload.get("task_title") or payload.get("title") or payload.get("subject")
        with st.container(border=True):
            st.markdown(f"**#{r['id']}  ·  {KIND_LABELS[r['kind']]}  ·  {r['code']}**  ·  {target}")

            if r["kind"] == "flag_conflict":
                st.warning("This would overwrite an existing date or owner. Check it against the evidence.")
            for field, change in payload.get("changes", {}).items():
                st.markdown(f"- **{field}**: {change['from']} → **{change['to']}**")
            if r["kind"] == "create_task":
                st.markdown(f"- due: {payload.get('due_date')}  ·  owner: {payload.get('owner')}")
            if payload.get("note"):
                st.markdown(f"- note: {payload['note']}")
            if r["kind"] == "client_update":
                if payload.get("unsupported"):
                    st.error("Some paragraphs have no valid citation. Check them before approving:\n\n"
                             + "\n".join(f"- {t}" for t in payload["unsupported"]))
                st.text(f"Subject: {payload['subject']}\n\n{payload['body']}")

            st.caption(f"Why: {r['reason']}")

            # The evidence: the exact client words this proposal is based on
            if r["cited_item_ids"]:
                evidence = query(
                    "select i.source_quote, d.title from extracted_items i "
                    "join documents d on d.id = i.document_id where i.id = any(%s)",
                    (r["cited_item_ids"],),
                )
                for e in evidence:
                    quote = " ".join(e["source_quote"].split())
                    st.markdown(f"> {quote}\n>\n> *{e['title']}*")

            note = st.text_input("Reviewer note (optional)", key=f"note_{r['id']}")
            approve_col, reject_col, _ = st.columns([1, 1, 6])
            if approve_col.button("Approve", key=f"approve_{r['id']}", type="primary"):
                review(r["id"], "approved", note)
            if reject_col.button("Reject", key=f"reject_{r['id']}"):
                review(r["id"], "rejected", note)


# ---------- Projects ----------

def projects_page():
    st.header("Projects")
    projects = {p["code"]: p for p in all_projects()}
    code = st.selectbox("Project", list(projects),
                        format_func=lambda c: f"{c}: {projects[c]['name']}")

    tasks = query(
        """
        select title, owner, due_date, status, blocked_reason, notes
        from tasks where project_id = %s
        order by status = 'done', due_date nulls last
        """,
        (projects[code]["id"],),
    )
    st.dataframe(tasks, hide_index=True)

    if st.button("Draft client status update", type="primary"):
        with st.spinner("Drafting from the tracker..."):
            r = draft_status_update(code)
        if r["pending_reviews"]:
            st.warning(f"{r['pending_reviews']} proposed changes for this project are still awaiting "
                       "review. The tracker may be out of date.")
        if r["unsupported"]:
            st.error("Some paragraphs have no valid citation:\n\n"
                     + "\n".join(f"- {t}" for t in r["unsupported"]))
        st.subheader("What's outstanding")
        for p in r["outstanding"]:
            st.markdown(f"- {p.text}  `{', '.join(p.citations)}`")
        st.subheader("Draft email")
        st.info(f"Sent to the review queue as #{r['proposal_id']}. Nothing is sent to the client automatically.")
        st.text(f"Subject: {r['subject']}\n\n{r['body']}")


# ---------- Layout ----------

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

waiting = query("select count(*) as n from proposed_changes where status = 'pending'")[0]["n"]
st.sidebar.title("Foreman")
st.sidebar.caption("Project coordination agent for Hollis & Grant Civil Engineers (fictional demo)")
page = st.sidebar.radio("Go to", ["Inbox", "Review queue", "Projects"])
st.sidebar.metric("Waiting for review", waiting)

{"Inbox": inbox_page, "Review queue": review_page, "Projects": projects_page}[page]()