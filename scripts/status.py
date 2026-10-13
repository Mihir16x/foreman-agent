import sys

from app.status import ProjectNotResolved, draft_status_update

name = " ".join(sys.argv[1:]) or "riverside"

try:
    r = draft_status_update(name)
except ProjectNotResolved as e:
    matches = e.args[0]
    if not matches:
        print(f"No project matches '{name}'.")
    else:
        print(f"'{name}' matches several projects. Which one?")
        for m in matches:
            print(f"  - {m['code']}: {m['name']}")
    sys.exit(1)

if r["pending_reviews"]:
    print(f"!! {r['pending_reviews']} proposed changes for this project are still awaiting review.")
    print("   The tracker may be out of date; review them before sending this update.\n")

print(f"=== {r['project']}: what's outstanding ===")
for p in r["outstanding"]:
    print(f"- {p.text}  {p.citations}")

print(f"\n=== Draft client email (proposal #{r['proposal_id']}, awaiting review) ===")
print(f"Subject: {r['subject']}\n")
print(r["body"])

if r["unsupported"]:
    print("\n!! Paragraphs without valid citations (check before sending):")
    for text in r["unsupported"]:
        print(f"  - {text}")