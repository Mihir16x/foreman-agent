import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute(Path("db/schema.sql").read_text())
    conn.execute(Path("db/seed.sql").read_text())

    projects = conn.execute("select count(*) from projects").fetchone()[0]
    tasks = conn.execute(
        "select status, count(*) from tasks group by status order by status"
    ).fetchall()

print(f"Projects: {projects}")
print("Tasks:", ", ".join(f"{status} {n}" for status, n in tasks))