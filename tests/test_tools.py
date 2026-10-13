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
    tasks = get_open_tasks(riverside["id"])
    statuses = {t["status"] for t in tasks}
    assert len(tasks) == 5                 # 7 Riverside tasks, 2 are done
    assert "done" not in statuses
    assert "blocked" in statuses


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