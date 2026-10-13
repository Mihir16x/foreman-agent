import html
from datetime import date

import streamlit as st

from app.db import connect
from app.graph.intake import intake_graph
from app.review import ReviewError, decide
from app.status import draft_status_update

st.set_page_config(page_title="Foreman", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600&display=swap');

    html, body, .stMarkdown, .stText, p, li, label { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3 { font-family: 'IBM Plex Sans Condensed', sans-serif !important; color: #1C2B36; letter-spacing: -0.01em; }
    .page-lede { color: #33434F; font-size: 1.05rem; margin: -0.5rem 0 1.5rem; max-width: 70ch; }

    .card-head { display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.25rem; }
    .card-title { font-size: 1.15rem; font-weight: 600; color: #1C2B36; }
    .card-meta { color: #4A5A66; font-size: 0.9rem; }

    .badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
    .badge-create_task  { background: #E3F1E5; color: #24552E; }
    .badge-update_task  { background: #E3ECF7; color: #1F3A5F; }
    .badge-flag_conflict { background: #FBEBC8; color: #6E4500; }
    .badge-client_update { background: #EEE8F7; color: #4B3478; }

    .revision { border: 1px solid #C9D3D0; background: #FFFFFF; border-radius: 4px; padding: 0.5rem 0.9rem; margin: 0.6rem 0; }
    .rev-row { display: grid; grid-template-columns: 7rem 1fr; gap: 0.75rem; padding: 0.3rem 0; }
    .rev-field { color: #4A5A66; font-weight: 500; }
    .rev-old { text-decoration: line-through; color: #9A3B2E; margin-right: 0.4rem; }
    .rev-new { font-weight: 600; color: #24552E; }
    .rev-empty { color: #6B7A84; font-style: italic; }
    .rev-note { color: #1C2B36; }

    .conflict-note { color: #6E4500; font-size: 0.95rem; margin: 0.4rem 0; }
    .reason { color: #33434F; font-size: 0.95rem; margin: 0.4rem 0; max-width: 75ch; }
    .reason b { color: #1C2B36; }

    .evidence { border-left: 3px solid #1F3A5F; background: #FFFFFF; padding: 0.6rem 0.9rem; margin: 0.6rem 0; color: #1C2B36; max-width: 75ch; }
    .evidence-source { display: block; margin-top: 0.35rem; font-size: 0.85rem; color: #4A5A66; }

    .doc-body, .email { background: #FFFFFF; border: 1px solid #C9D3D0; border-radius: 4px; padding: 1rem 1.2rem;
                        white-space: pre-wrap; line-height: 1.55; color: #1C2B36; max-width: 72ch; }
    .warn-list { color: #9A3B2E; }
    </style>
    """,
    unsafe_allow_html=True,
)

KINDS = {
    "create_task": "New task",
    "update_task": "Update",
    "flag_conflict": "Conflict",
    "client_update": "Client email",
}
FIELDS = {"due_date": "Due date", "owner": "Owner", "status": "Status"}


# ---------- Helpers ----------

def query(sql: str, params=()) -> list[dict]:
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def all_projects() -> list[dict]:
    return query("select id, code, name, client_name from projects order by code")


def e(value) -> str:
    """Escape text before putting it in HTML, so client text can't break the page."""
    return html.escape(str(value))


def fmt(value) -> str:
    """Show dates as 'Oct 5, 2026'; anything else as-is."""
    if value is None:
        return "none"
    try:
        d = date.fromisoformat(str(value))
        return f"{d:%b} {d.day}, {d.year}"
    except ValueError:
        return str(value)


def flash(message: str) -> None:
    st.session_state["flash"] = message
    st.rerun()


def lede(text: str) -> None:
    st.markdown(f'<p class="page-lede">{e(text)}</p>', unsafe_allow_html=True)


# ---------- Inbox ----------

def doc_status(d: dict) -> tuple[str, str]:
    """Label and color for a document, based on its proposals' current status."""
    if d["intake_status"] == "proposed":
        return (f"{d['pending']} to review", "orange") if d["pending"] else ("Reviewed", "green")
    return {
        "new": ("Not read yet", "blue"),
        "no_changes": ("No changes needed", "gray"),
        "no_items": ("Nothing to act on", "gray"),
        "needs_manual_review": ("Needs a person to read it", "red"),
    }[d["intake_status"]]


def inbox_page():
    st.title("Inbox")
    lede("Client emails, meeting notes and RFIs. Foreman reads each one and proposes changes to the tracker.")

    with st.expander("Add a document"):
        projects = {"Not filed under a project": None} | {
            f"{p['code']}: {p['name']}": p["id"] for p in all_projects()
        }
        with st.form("add_document", clear_on_submit=True):
            project_label = st.selectbox("Project", list(projects))
            kind = st.selectbox("Kind", ["email", "meeting_note", "rfi", "report"],
                                format_func=lambda k: k.replace("_", " ").capitalize())
            title = st.text_input("Title")
            text = st.text_area("Text", height=200)
            submitted = st.form_submit_button("Add and read", type="primary")
        if submitted:
            if not title.strip() or not text.strip():
                st.error("Add a title and the document text, then try again.")
            else:
                with connect() as conn:
                    doc_id = conn.execute(
                        "insert into documents (project_id, kind, title, raw_text) "
                        "values (%s, %s, %s, %s) returning id",
                        (projects[project_label], kind, title, text),
                    ).fetchone()["id"]
                with st.spinner("Foreman is reading the document..."):
                    result = intake_graph.invoke({"document_id": doc_id})
                n = len(result.get("proposals", []))
                flash(f"Read '{title}'. {n} proposed change{'s' if n != 1 else ''} added to the review queue.")

    new_ids = [r["id"] for r in query(
        "select id from documents where intake_status = 'new' order by received_at, id")]
    if new_ids and st.button(f"Read {len(new_ids)} new documents", type="primary"):
        progress = st.progress(0.0)
        for n, doc_id in enumerate(new_ids, 1):
            intake_graph.invoke({"document_id": doc_id})
            progress.progress(n / len(new_ids))
        flash(f"Read {len(new_ids)} documents.")

    documents = query(
        """
        select d.id, d.title, d.received_at::date as received, d.intake_status, d.raw_text, p.code,
               (select count(*) from proposed_changes c
                where c.status = 'pending'
                  and c.cited_item_ids && array(select i.id from extracted_items i
                                                where i.document_id = d.id)) as pending
        from documents d left join projects p on p.id = d.project_id
        order by d.received_at desc, d.id desc
        """
    )
    for d in documents:
        status, color = doc_status(d)
        label = f"{d['title']}  ({d['code'] or 'not filed'}, {d['received']:%b %d})  :{color}[{status}]"
        with st.expander(label):
            left, right = st.columns([3, 2], gap="large")
            with left:
                st.markdown(f'<div class="doc-body">{e(d["raw_text"].strip())}</div>',
                            unsafe_allow_html=True)
            with right:
                items = query(
                    "select type, summary, due_date, owner from extracted_items "
                    "where document_id = %s order by id",
                    (d["id"],),
                )
                st.subheader("What Foreman found")
                if not items:
                    st.write("Nothing to act on in this document.")
                for it in items:
                    details = [f"due {fmt(it['due_date'])}" if it["due_date"] else None,
                               f"owner {it['owner']}" if it["owner"] else None]
                    extra = ", ".join(x for x in details if x)
                    st.markdown(f"**{it['type'].replace('_', ' ').capitalize()}:** {it['summary']}"
                                + (f"  \n{extra}" if extra else ""))


# ---------- Review queue ----------

def revision_block(kind: str, payload: dict) -> str:
    rows = []
    if kind == "create_task":
        for label, value in (("Due date", payload.get("due_date")), ("Owner", payload.get("owner"))):
            rows.append((label, f'<span class="rev-new">{e(fmt(value))}</span>' if value
                         else '<span class="rev-empty">Not stated</span>'))
    for field, change in payload.get("changes", {}).items():
        rows.append((FIELDS.get(field, field),
                     f'<span class="rev-old">{e(fmt(change["from"]))}</span>'
                     f'<span class="rev-new">{e(fmt(change["to"]))}</span>'))
    if payload.get("note"):
        rows.append(("Note", f'<span class="rev-note">{e(payload["note"])}</span>'))
    if not rows:
        return ""
    body = "".join(f'<div class="rev-row"><span class="rev-field">{e(f)}</span><span>{v}</span></div>'
                   for f, v in rows)
    return f'<div class="revision">{body}</div>'


def review(proposal_id: int, decision: str, note: str) -> None:
    try:
        decide(proposal_id, decision, note or None)
    except ReviewError as err:
        st.error(f"Change #{proposal_id} was not applied: {err}")
        return
    flash(f"Change #{proposal_id} {decision}.")


def review_page():
    st.title("Review queue")
    proposals = query(
        """
        select c.id, c.kind, c.payload, c.reason, c.cited_item_ids, p.code, p.name
        from proposed_changes c join projects p on p.id = c.project_id
        where c.status = 'pending'
        order by c.id
        """
    )
    if not proposals:
        lede("Nothing is waiting. New proposals appear here after Foreman reads a document.")
        return
    lede(f"{len(proposals)} proposed changes. Nothing changes in the tracker until you approve it.")

    for r in proposals:
        p = r["payload"]
        target = p.get("task_title") or p.get("title") or p.get("subject")
        with st.container(border=True):
            st.markdown(
                f'<div class="card-head"><span class="badge badge-{r["kind"]}">{KINDS[r["kind"]]}</span>'
                f'<span class="card-title">{e(target)}</span></div>'
                f'<div class="card-meta">{e(r["code"])}, {e(r["name"])}  (change #{r["id"]})</div>',
                unsafe_allow_html=True,
            )
            if r["kind"] == "flag_conflict":
                st.markdown('<p class="conflict-note">This replaces a value already in the tracker. '
                            "Check it against the client's words below.</p>", unsafe_allow_html=True)

            if r["kind"] == "client_update":
                if p.get("unsupported"):
                    items = "".join(f"<li>{e(t)}</li>" for t in p["unsupported"])
                    st.markdown(f'<p class="conflict-note">These paragraphs have no supporting fact. '
                                f'Check them before approving:</p><ul class="warn-list">{items}</ul>',
                                unsafe_allow_html=True)
                st.markdown(f'<div class="email"><b>{e(p["subject"])}</b>\n\n{e(p["body"])}</div>',
                            unsafe_allow_html=True)
            else:
                st.markdown(revision_block(r["kind"], p), unsafe_allow_html=True)

            st.markdown(f'<p class="reason"><b>Why:</b> {e(r["reason"])}</p>', unsafe_allow_html=True)

            if r["cited_item_ids"]:
                evidence = query(
                    "select i.source_quote, d.title, d.received_at::date as received "
                    "from extracted_items i join documents d on d.id = i.document_id "
                    "where i.id = any(%s)",
                    (r["cited_item_ids"],),
                )
                for ev in evidence:
                    quote = " ".join(ev["source_quote"].split())
                    st.markdown(
                        f'<div class="evidence">"{e(quote)}"'
                        f'<span class="evidence-source">{e(ev["title"])}, received {fmt(ev["received"])}</span></div>',
                        unsafe_allow_html=True,
                    )

            note = st.text_input("Reviewer note (optional)", key=f"note_{r['id']}")
            approve_col, reject_col, _ = st.columns([1, 1, 5])
            if approve_col.button("Approve", key=f"approve_{r['id']}", type="primary",
                                  use_container_width=True):
                review(r["id"], "approved", note)
            if reject_col.button("Reject", key=f"reject_{r['id']}", use_container_width=True):
                review(r["id"], "rejected", note)


# ---------- Projects ----------

def projects_page():
    projects = {p["code"]: p for p in all_projects()}
    code = st.selectbox("Project", list(projects),
                        format_func=lambda c: f"{c}: {projects[c]['name']}")
    project = projects[code]

    st.title(project["name"])
    tasks = query(
        """
        select title, owner, due_date, status, blocked_reason, notes
        from tasks where project_id = %s
        order by status = 'done', due_date nulls last
        """,
        (project["id"],),
    )
    open_tasks = [t for t in tasks if t["status"] != "done"]
    blocked = [t for t in tasks if t["status"] == "blocked"]
    overdue = [t for t in open_tasks if t["due_date"] and t["due_date"] < date.today()]
    lede(f"Client: {project['client_name']}. {len(open_tasks)} open tasks, "
         f"{len(blocked)} blocked, {len(overdue)} overdue.")

    st.dataframe(
        tasks,
        hide_index=True,
        use_container_width=True,
        column_config={
            "title": st.column_config.TextColumn("Task", width="large"),
            "owner": "Owner",
            "due_date": st.column_config.DateColumn("Due", format="MMM D, YYYY"),
            "status": "Status",
            "blocked_reason": "Waiting on",
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )

    if st.button("Draft client status update", type="primary"):
        with st.spinner("Writing the update from the tracker..."):
            r = draft_status_update(code)
        if r["pending_reviews"]:
            st.warning(f"{r['pending_reviews']} proposed changes for this project are still waiting "
                       "for review, so the tracker may be out of date.")
        if r["unsupported"]:
            st.error("Some paragraphs have no supporting fact:\n\n"
                     + "\n".join(f"- {t}" for t in r["unsupported"]))

        left, right = st.columns([2, 3], gap="large")
        with left:
            st.subheader("What's outstanding")
            for p in r["outstanding"]:
                st.markdown(f"- {p.text}")
        with right:
            st.subheader("Draft email")
            st.markdown(f'<div class="email"><b>{e(r["subject"])}</b>\n\n{e(r["body"])}</div>',
                        unsafe_allow_html=True)
            st.caption(f"Added to the review queue as change #{r['proposal_id']}. "
                       "Nothing is sent to the client automatically.")


# ---------- Layout ----------

if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

waiting = query("select count(*) as n from proposed_changes where status = 'pending'")[0]["n"]
st.sidebar.title("Foreman")
st.sidebar.write("Project coordination for Hollis & Grant Civil Engineers. A demo with fictional data.")
page = st.sidebar.radio("Go to", ["Inbox", "Review queue", "Projects"], label_visibility="collapsed")
st.sidebar.markdown(f"**{waiting}** changes waiting for review")

{"Inbox": inbox_page, "Review queue": review_page, "Projects": projects_page}[page]()