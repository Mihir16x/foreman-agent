from pathlib import Path

import yaml

from app.db import connect

with connect() as conn:
    # Start fresh each time so running this twice doesn't duplicate documents
    conn.execute("truncate documents restart identity cascade")

    for path in sorted(Path("evals/cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        project = conn.execute(
            "select id from projects where code = %s", (case["project"],)
        ).fetchone()
        conn.execute(
            """
            insert into documents (project_id, kind, title, received_at, raw_text)
            values (%s, %s, %s, %s, %s)
            """,
            (project["id"] if project else None, case["kind"], case["title"],
             case["received"], case["text"]),
        )

    counts = conn.execute(
        "select count(*) as total, count(project_id) as assigned from documents"
    ).fetchone()

print(f"Loaded {counts['total']} documents ({counts['assigned']} assigned to a project)")