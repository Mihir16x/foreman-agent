import sys
from pathlib import Path

import yaml

from app.db import connect
from app.extract import extract_items

case_id = sys.argv[1] if len(sys.argv) > 1 else "case_01"
case = yaml.safe_load(Path(f"evals/cases/{case_id}.yaml").read_text(encoding="utf-8"))

with connect() as conn:
    projects = conn.execute(
        "select code, name, client_name, client_email from projects order by code"
    ).fetchall()

kept, dropped = extract_items(case["title"], case["text"], case["received"], projects, case["project"])

print(f"\n=== Foreman found {len(kept)} ===")
for item in kept:
    print(f"- [{item.type}] {item.project_code} | {item.summary}")
    print(f"    due: {item.due_date} | owner: {item.owner} | confidence: {item.confidence}")
    print(f'    quote: "{item.source_quote}"')

if dropped:
    print(f"\n=== Dropped {len(dropped)} (quote not found in document) ===")
    for item in dropped:
        print(f'- [{item.type}] {item.summary}  quote: "{item.source_quote}"')

print(f"\n=== Answer key {len(case['expected'])} ===")
for exp in case["expected"]:
    print(f"- [{exp['type']}] {exp['project']} | {exp['summary']}")
    print(f"    due: {exp['due_date']} | owner: {exp['owner']}")