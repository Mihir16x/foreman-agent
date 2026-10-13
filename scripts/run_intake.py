import sys

from app.db import connect
from app.graph.intake import intake_graph

# Process one document by id, or every document that hasn't been processed yet
with connect() as conn:
    if len(sys.argv) > 1:
        document_ids = [int(sys.argv[1])]
    else:
        document_ids = [
            row["id"] for row in conn.execute(
                "select id from documents where intake_status = 'new' order by received_at, id"
            ).fetchall()
        ]

for document_id in document_ids:
    result = intake_graph.invoke({"document_id": document_id})
    title = result.get("document", {}).get("title", "?")
    print(f"\n[{document_id}] {title}  ->  {result['status']}")
    for p in result.get("proposals", []):
        target = p["payload"].get("task_title") or p["payload"].get("title")
        print(f"    #{p['id']} {p['kind']}: {target}")
    for s in result.get("skipped", []):
        print(f"    skipped: {s['item']}  ({s['why']})")
    if result.get("error"):
        print(f"    error: {result['error']}")