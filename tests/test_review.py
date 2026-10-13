from datetime import date

import pytest

from app.db import connect
from app.review import ReviewError, decide
from app.tools import find_project, propose_change


@pytest.fixture
def task():
    """A throwaway Riverside task due Nov 1, cleaned up after each test."""
    project = find_project("riverside")[0]
    with connect() as conn:
        row = conn.execute(
            """
            insert into tasks (project_id, title, owner, due_date)
            values (%s, 'Test task', 'Alex Romero', '2026-11-01') returning id
            """,
            (project["id"],),
        ).fetchone()
    yield {"id": row["id"], "project_id": project["id"]}
    with connect() as conn:
        conn.execute("delete from proposed_changes where reason like 'test:%'")
        conn.execute("delete from tasks where title like 'Test task%'")


def propose_new_date(task, new_date):
    return propose_change(
        task["project_id"], "flag_conflict",
        {"task_id": task["id"], "task_title": "Test task", "note": None,
         "changes": {"due_date": {"from": date(2026, 11, 1), "to": new_date}}},
        "test: client moved the date", [],
    )


def due_date_of(task_id):
    with connect() as conn:
        return conn.execute("select due_date from tasks where id = %s", (task_id,)).fetchone()["due_date"]


def test_approving_a_conflict_changes_the_date(task):
    decide(propose_new_date(task, date(2026, 10, 20)), "approved")
    assert due_date_of(task["id"]) == date(2026, 10, 20)


def test_rejecting_changes_nothing(task):
    decide(propose_new_date(task, date(2026, 10, 20)), "rejected", "client kept the original date")
    assert due_date_of(task["id"]) == date(2026, 11, 1)


def test_a_proposal_cannot_be_decided_twice(task):
    proposal_id = propose_new_date(task, date(2026, 10, 20))
    decide(proposal_id, "rejected")
    with pytest.raises(ReviewError, match="already"):
        decide(proposal_id, "approved")


def test_stale_proposal_is_refused(task):
    first = propose_new_date(task, date(2026, 10, 20))
    second = propose_new_date(task, date(2026, 10, 25))  # also assumes the date is still Nov 1
    decide(first, "approved")
    with pytest.raises(ReviewError, match="changed since"):
        decide(second, "approved")
    assert due_date_of(task["id"]) == date(2026, 10, 20)  # second one changed nothing


def test_approving_create_task_adds_it(task):
    proposal_id = propose_change(
        task["project_id"], "create_task",
        {"title": "Test task created", "due_date": date(2026, 12, 1), "owner": None},
        "test: new work", [],
    )
    decide(proposal_id, "approved")
    with connect() as conn:
        row = conn.execute(
            "select status, due_date from tasks where title = 'Test task created'"
        ).fetchone()
    assert row["status"] == "open"
    assert row["due_date"] == date(2026, 12, 1)