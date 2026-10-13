from datetime import date

from app.models import TaskMatch
from app.reconcile import build_proposals

TASKS = [
    {"id": 1, "title": "Prepare bid documents", "owner": "Jordan Lee",
     "due_date": date(2026, 12, 4), "status": "open", "blocked_reason": None},
    {"id": 2, "title": "Submit stormwater permit application", "owner": "Morgan Hale",
     "due_date": date(2026, 10, 23), "status": "blocked", "blocked_reason": "Waiting on form"},
]
ITEMS = [
    {"id": 10, "type": "deadline", "summary": "Bid documents now due November 20",
     "due_date": date(2026, 11, 20), "owner": None},
    {"id": 11, "type": "request", "summary": "Submit the permit application now",
     "due_date": None, "owner": None},
]


def test_changing_an_existing_date_is_a_conflict():
    match = TaskMatch(item_index=0, action="update_task", task_id=1,
                      new_due_date=date(2026, 11, 20), reason="client moved the date")
    [proposal], _ = build_proposals(ITEMS, TASKS, [match])
    assert proposal["kind"] == "flag_conflict"
    assert proposal["payload"]["changes"]["due_date"] == {
        "from": date(2026, 12, 4), "to": date(2026, 11, 20)
    }


def test_unblocking_a_task_is_a_plain_update():
    match = TaskMatch(item_index=1, action="update_task", task_id=2,
                      new_status="open", reason="form received")
    [proposal], _ = build_proposals(ITEMS, TASKS, [match])
    assert proposal["kind"] == "update_task"


def test_unknown_task_id_becomes_a_new_task():
    match = TaskMatch(item_index=1, action="update_task", task_id=999, reason="model guessed")
    [proposal], _ = build_proposals(ITEMS, TASKS, [match])
    assert proposal["kind"] == "create_task"

def test_item_without_a_decision_is_reported_not_dropped():
    match = TaskMatch(item_index=0, action="update_task", task_id=1,
                      new_due_date=date(2026, 11, 20), reason="client moved the date")
    proposals, skipped = build_proposals(ITEMS, TASKS, [match])  # nothing for item 1
    assert len(proposals) == 1
    assert skipped == [{"item": "Submit the permit application now",
                        "why": "model returned no decision"}]