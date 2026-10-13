from app.tools import find_project, search_documents
from datetime import date

from app.db import connect
from app.tools import find_project, get_open_tasks, propose_change, search_documents


def test_find_project_by_partial_name():
    matches = find_project("riverside")
    assert [m["code"] for m in matches] == ["RVS-2041"]


def test_find_project_returns_empty_when_unknown():
    assert find_project("airport") == []


def test_search_finds_the_culvert_meeting():
    riverside = find_project("riverside")[0]
    results = search_documents(riverside["id"], "culvert")
    assert results[0]["title"] == "Riverside internal design meeting"


def test_search_stays_within_one_project():
    oak = find_project("oak street")[0]
    assert search_documents(oak["id"], "culvert") == []

def test_open_tasks_skip_done_but_include_blocked():
    riverside = find_project("riverside")[0]
    with connect() as conn:
        conn.execute(
            """
            insert into tasks (project_id, title, status, blocked_reason) values
              (%s, 'Test task blocked', 'blocked', 'waiting on test'),
              (%s, 'Test task done', 'done', null)
            """,
            (riverside["id"], riverside["id"]),
        )
    try:
        titles = {t["title"] for t in get_open_tasks(riverside["id"])}
        assert "Test task blocked" in titles   # blocked work still counts as open
        assert "Test task done" not in titles  # finished work doesn't
    finally:
        with connect() as conn:
            conn.execute("delete from tasks where title like 'Test task%'")


def test_propose_change_creates_a_pending_proposal():
    riverside = find_project("riverside")[0]
    proposal_id = propose_change(
        riverside["id"], "create_task",
        {"title": "Test task", "due_date": date(2026, 11, 1)},
        "test proposal", [],
    )
    with connect() as conn:
        row = conn.execute(
            "select status, payload from proposed_changes where id = %s", (proposal_id,)
        ).fetchone()
        conn.execute("delete from proposed_changes where id = %s", (proposal_id,))  # clean up

    assert row["status"] == "pending"
    assert row["payload"]["due_date"] == "2026-11-01"