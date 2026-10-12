import json
import time
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.db import connect
from app.extract import ExtractionFailed, extract_items, get_llm

PAUSE_SECONDS = 4  # small pause between cases to avoid rate limits
CHECKED_FIELDS = ["type", "project", "due_date", "owner"]


# ---------- Step 2: the judge that pairs up items ----------

class Pair(BaseModel):
    expected_index: int
    found_index: int


class Judgement(BaseModel):
    pairs: list[Pair]


JUDGE_PROMPT = """Two lists of items were taken from the same document: one written by a human reviewer (EXPECTED) and one produced by a system (FOUND).

Pair each FOUND item with the EXPECTED item that describes the same real-world request, task, deadline, or decision. Ignore differences in wording, and use the document to understand who people are (for example, a named person may work for the client). Use each item at most once. Leave an item unpaired if nothing matches.

EXPECTED:
{expected}

FOUND:
{found}

DOCUMENT THE ITEMS CAME FROM:
{document}
"""


def numbered(items: list[dict]) -> str:
    return "\n".join(
        f"{i}. [{item['type']}] {item['summary']} (owner: {item['owner']}, due: {item['due_date']})"
        for i, item in enumerate(items)
    )


def pair_items(expected: list[dict], found: list[dict], document: str) -> list[tuple[int, int]]:
    """Ask the judge which items match. Returns (expected_index, found_index) pairs."""
    if not expected or not found:
        return []
    judge = get_llm().with_structured_output(Judgement)
    result = judge.invoke(JUDGE_PROMPT.format(
        expected=numbered(expected), found=numbered(found), document=document
    ))
    if result is None:
        return []

    # Don't trust the judge blindly: drop out-of-range or reused indexes.
    pairs, used_e, used_f = [], set(), set()
    for p in result.pairs:
        valid = 0 <= p.expected_index < len(expected) and 0 <= p.found_index < len(found)
        if valid and p.expected_index not in used_e and p.found_index not in used_f:
            pairs.append((p.expected_index, p.found_index))
            used_e.add(p.expected_index)
            used_f.add(p.found_index)
    return pairs


# ---------- Step 3: plain-Python field checks ----------

def same(a, b) -> bool:
    """Exact match for dates and codes; names match if one contains the other ("Casey" vs "Casey Brooks")."""
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, str) and isinstance(b, str):
        a, b = a.lower().strip(), b.lower().strip()
        return a == b or a in b or b in a
    return a == b


# ---------- Run every case ----------

def main():
    with connect() as conn:
        projects = conn.execute(
            "select code, name, client_name, client_email from projects order by code"
        ).fetchall()

    total_expected = total_found = total_correct = 0
    report = []

    for path in sorted(Path("evals/cases").glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        expected = case["expected"]
        problems = []

        # Step 1: Foreman takes the test
        try:
            kept, dropped = extract_items(
                case["title"], case["text"], case["received"], projects, case["project"]
            )
        except ExtractionFailed as e:
            kept, dropped = [], []
            problems.append(f"extraction failed: {e}")

        found = [
            {"type": i.type, "project": i.project_code, "summary": i.summary,
             "due_date": i.due_date, "owner": i.owner}
            for i in kept
        ]

        # Step 2: pair up the answers (a failed judge call is recorded, not fatal)
        try:
            pairs = pair_items(expected, found, case["text"])
        except Exception as e:
            pairs = []
            problems.append(f"judge failed: {type(e).__name__}")

        # Step 3: check the details of each pair
        correct = 0
        for e_idx, f_idx in pairs:
            wrong = [f for f in CHECKED_FIELDS if not same(expected[e_idx][f], found[f_idx][f])]
            if wrong:
                details = ", ".join(
                    f"{f} expected {expected[e_idx][f]} got {found[f_idx][f]}" for f in wrong
                )
                problems.append(f"wrong fields on '{expected[e_idx]['summary']}': {details}")
            else:
                correct += 1

        # Step 4: list missed and extra items
        paired_e = {e for e, _ in pairs}
        paired_f = {f for _, f in pairs}
        problems += [f"missed: {x['summary']}" for i, x in enumerate(expected) if i not in paired_e]
        problems += [f"extra: {x['summary']}" for i, x in enumerate(found) if i not in paired_f]
        problems += [f"dropped by quote check: {d.summary}" for d in dropped]

        total_expected += len(expected)
        total_found += len(found)
        total_correct += correct

        print(f"{case['id']}  expected {len(expected)}  found {len(found)}  correct {correct}")
        for problem in problems:
            print(f"    - {problem}")

        report.append({"case": case["id"], "expected": expected, "found": found,
                       "correct": correct, "problems": problems})
        time.sleep(PAUSE_SECONDS)

    precision = total_correct / total_found if total_found else 0
    recall = total_correct / total_expected if total_expected else 0

    print()
    print(f"Precision: {precision:.2f}  ({total_correct} of {total_found} found items fully correct)")
    print(f"Recall:    {recall:.2f}  ({total_correct} of {total_expected} expected items found and correct)")

    out_dir = Path("evals/results")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{datetime.now():%Y-%m-%d_%H%M}.json"
    out_path.write_text(json.dumps(
        {"precision": precision, "recall": recall, "cases": report}, indent=2, default=str
    ))
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()