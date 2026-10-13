from datetime import date

from app.db import connect

# Only these task columns can ever be changed by a proposal.
EDITABLE_FIELDS = {"due_date", "owner", "status", "blocked_reason", "notes"}


class ReviewError(Exception):
    """The decision could not be applied. Nothing was changed."""


def as_text(value):
    """Compare DB values (dates) with JSON values (strings) on equal terms."""
    return None if value is None else str(value)


def decide(proposal_id: int, decision: str, reviewer_note: str | None = None) -> None:
    """Approve or reject a proposal. The tracker change and the decision are saved together, or not at all."""
    if decision not in ("approved", "rejected"):
        raise ReviewError(f"unknown decision {decision!r}")

    # Everything inside this block is one transaction: any error rolls all of it back.
    with connect() as conn:
        proposal = conn.execute(
            "select * from proposed_changes where id = %s for update", (proposal_id,)
        ).fetchone()
        if proposal is None:
            raise ReviewError("proposal not found")
        if proposal["status"] != "pending":
            raise ReviewError(f"proposal already {proposal['status']}")

        if decision == "approved":
            apply_change(conn, proposal)

        conn.execute(
            """
            update proposed_changes
            set status = %s, reviewer_note = %s, decided_at = now()
            where id = %s
            """,
            (decision, reviewer_note, proposal_id),
        )


def apply_change(conn, proposal: dict) -> None:
    payload, kind = proposal["payload"], proposal["kind"]

    if kind == "create_task":
        source_item = proposal["cited_item_ids"][0] if proposal["cited_item_ids"] else None
        conn.execute(
            """
            insert into tasks (project_id, title, owner, due_date, source_item_id)
            values (%s, %s, %s, %s, %s)
            """,
            (proposal["project_id"], payload["title"], payload.get("owner"),
             payload.get("due_date"), source_item),
        )
        return

    if kind in ("update_task", "flag_conflict"):
        task = conn.execute(
            "select * from tasks where id = %s and project_id = %s for update",
            (payload["task_id"], proposal["project_id"]),
        ).fetchone()
        if task is None:
            raise ReviewError("task no longer exists")

        # Stale check: every field must still hold the value the proposal was based on.
        for field, change in payload["changes"].items():
            if as_text(task[field]) != as_text(change["from"]):
                raise ReviewError(
                    f"task changed since this was proposed: {field} is now "
                    f"{task[field]}, proposal expected {change['from']}"
                )

        updates = {field: change["to"] for field, change in payload["changes"].items()}
        if updates.get("status") == "open":
            updates["blocked_reason"] = None
        if updates.get("status") == "blocked":
            updates["blocked_reason"] = payload.get("note") or "On hold per client"
        if payload.get("note"):
            stamped = f"[{date.today()}] {payload['note']}"
            updates["notes"] = f"{task['notes']}\n{stamped}" if task["notes"] else stamped

        if not set(updates) <= EDITABLE_FIELDS:
            raise ReviewError(f"proposal tries to change protected fields: {set(updates) - EDITABLE_FIELDS}")

        if updates:
            assignments = ", ".join(f"{field} = %s" for field in updates)
            conn.execute(
                f"update tasks set {assignments}, updated_at = now() where id = %s",
                (*updates.values(), task["id"]),
            )
        return

    if kind == "client_update":
        return  # V1: approval marks it ready to send; nothing is sent automatically

    raise ReviewError(f"unknown proposal kind {kind!r}")