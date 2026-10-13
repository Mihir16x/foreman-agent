from app.extract import get_llm
from app.models import Reconciliation, TaskMatch
from app.prompts import RECONCILE_PROMPT
from app.tools import get_open_tasks, propose_change


def format_tasks(tasks: list[dict]) -> str:
    lines = []
    for t in tasks:
        line = f"- [task_id {t['id']}] {t['title']} | owner: {t['owner']} | due: {t['due_date']} | status: {t['status']}"
        if t["blocked_reason"]:
            line += f" ({t['blocked_reason']})"
        lines.append(line)
    return "\n".join(lines) or "(no open tasks)"


def format_items(items: list[dict]) -> str:
    return "\n".join(
        f"{i}. [{item['type']}] {item['summary']} | due: {item['due_date']} | owner: {item['owner']}"
        for i, item in enumerate(items)
    )


def build_proposals(items: list[dict], tasks: list[dict], matches: list[TaskMatch]):
    """Turn the model's matches into proposals, applying the firm's rules in code.

    Returns (proposals, skipped). Every item ends up in one of the two lists:
    nothing is dropped silently.
    """
    tasks_by_id = {t["id"]: t for t in tasks}
    proposals, skipped, decided = [], [], set()

    for m in matches:
        if not 0 <= m.item_index < len(items) or m.item_index in decided:
            continue  # unknown or repeated item number from the model
        decided.add(m.item_index)
        item = items[m.item_index]
        task = tasks_by_id.get(m.task_id)
        action = m.action

        # The model pointed at a task that isn't open in this project: don't trust it.
        if action == "update_task" and task is None:
            action = "create_task"

        if action == "no_change":
            skipped.append({"item": item["summary"], "why": f"model chose no_change: {m.reason}"})
            continue

        if action == "create_task":
            proposals.append({
                "kind": "create_task",
                "payload": {"title": m.new_title or item["summary"],
                            "due_date": m.new_due_date, "owner": m.new_owner},
                "reason": m.reason,
                "cited_item_ids": [item["id"]],
            })
            continue

        # update_task: record only fields that actually change, with before and after values
        changes = {}
        for field, new_value in (("due_date", m.new_due_date), ("owner", m.new_owner),
                                 ("status", m.new_status)):
            if new_value is not None and new_value != task[field]:
                changes[field] = {"from": task[field], "to": new_value}

        if not changes and not m.note:
            skipped.append({"item": item["summary"],
                            "why": f"update on task {task['id']} changes nothing: {m.reason}"})
            continue

        # Business rule: overwriting an existing date or owner is a conflict for a human to decide.
        conflict = any(f in changes and task[f] is not None for f in ("due_date", "owner"))

        proposals.append({
            "kind": "flag_conflict" if conflict else "update_task",
            "payload": {"task_id": task["id"], "task_title": task["title"],
                        "changes": changes, "note": m.note},
            "reason": m.reason,
            "cited_item_ids": [item["id"]],
        })

    # Items the model never gave a decision for
    for i, item in enumerate(items):
        if i not in decided:
            skipped.append({"item": item["summary"], "why": "model returned no decision"})

    return proposals, skipped


def reconcile(project: dict, items: list[dict], received, document: str):
    """Match one project's new items against its tracker and write proposals to the review queue.

    Returns (saved, skipped): saved is a list of (proposal_id, proposal).
    """
    tasks = get_open_tasks(project["id"])
    prompt = RECONCILE_PROMPT.format(
        project=f"{project['code']}: {project['name']}",
        tasks=format_tasks(tasks),
        items=format_items(items),
        received=received,
        document=document,
    )
    result = get_llm().with_structured_output(Reconciliation).invoke(prompt)
    proposals, skipped = build_proposals(items, tasks, result.matches if result else [])

    saved = []
    for p in proposals:
        proposal_id = propose_change(project["id"], p["kind"], p["payload"],
                                     p["reason"], p["cited_item_ids"])
        saved.append((proposal_id, p))
    return saved, skipped