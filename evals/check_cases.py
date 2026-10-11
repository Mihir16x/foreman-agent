from pathlib import Path

import yaml

total = 0
for path in sorted(Path("evals/cases").glob("*.yaml")):
    case = yaml.safe_load(path.read_text(encoding="utf-8"))
    n = len(case["expected"])
    total += n
    print(f"{case['id']}: {n} expected items ({case['kind']}, {case['project']})")

print(f"Total expected items: {total}")