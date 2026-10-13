import sys

from app.db import connect
from app.review import ReviewError, decide

if len(sys.argv) == 1:
    # No arguments: list pending proposals
    with connect() as conn:
        rows = conn.execute(
            """
            select c.id, p.code, c.kind, c.payload, c.reason
            from proposed_changes c join projects p on p.id = c.project_id
            where c.status = 'pending'
            order by c.id
            """
        ).fetchall()
    for r in rows:
        target = r["payload"].get("task_title") or r["payload"].get("title")
        print(f"#{r['id']} {r['code']} [{r['kind']}] {target}")
        if r["payload"].get("changes"):
            print(f"    changes: {r['payload']['changes']}")
        if r["payload"].get("note"):
            print(f"    note: {r['payload']['note']}")
else:
    # python -m scripts.review <id> approve|reject [note...]
    proposal_id, action = int(sys.argv[1]), sys.argv[2]
    decision = {"approve": "approved", "reject": "rejected"}[action]
    note = " ".join(sys.argv[3:]) or None
    try:
        decide(proposal_id, decision, note)
        print(f"#{proposal_id} {decision}")
    except ReviewError as e:
        print(f"#{proposal_id} not applied: {e}")