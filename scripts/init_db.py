import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()
schema = Path("db/schema.sql").read_text()

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute(schema)
    tables = conn.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' order by table_name"
    ).fetchall()

print("Tables created:", ", ".join(t[0] for t in tables))