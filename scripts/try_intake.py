import sys
from pathlib import Path

import yaml

from app.db import connect
from app.extract import extract_items
from app.reconcile import reconcile
from app.tools import save_extracted_items

case_id = sys.argv[1] if len(sys.argv) > 1 else "case_10"
case = yaml.safe_load(Path(f"evals/cases/{case_id}.yaml").read_text(encoding="utf-8"))

with connect() as conn:
    projects = conn.execute(
        "select id, code, name, client_name, client_email from projects order by code"
    ).fetchall()
    document = conn.execute(
        "select id from documents where title = %s", (case["title"],)
    ).fetchone()

# 1. Read the document
kept, dropped = extract_items(case["title"], case["text"], case["received"], projects, case["project"])
item_ids = save_extracted_items(document["id"], kept)
print(f"Extracted {len(kept)} items ({len(dropped)} dropped by quote check)")

items = [
    {"id": item_id, "type": it.type, "summary": it.summary, "due_date": it.due_date,
     "owner": it.owner, "project_code": it.project_code}
    for item_id, it in zip(item_ids, kept)
]

# 2. Reconcile each project's items against its tracker
projects_by_code = {p["code"]: p for p in projects}
for code in sorted({i["project_code"] for i in items if i["project_code"]}):
    project_items = [i for i in items if i["project_code"] == code]
    results, skipped = reconcile(projects_by_code[code], project_items, case["received"], case["text"])
    print(f"\n=== {code}: {len(results)} proposals ===")
    for proposal_id, p in results:
        print(f"#{proposal_id} [{p['kind']}] {p['reason']}")
        print(f"    {p['payload']}")
    for s in skipped:
        print(f"  skipped: {s['item']}")
        print(f"      why: {s['why']}")

unassigned = [i for i in items if not i["project_code"]]
if unassigned:
    print(f"\n{len(unassigned)} items have no project and need manual review")