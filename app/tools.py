from app.db import connect
import json

from psycopg.types.json import Jsonb


def find_project(text: str) -> list[dict]:
    """Find projects whose name or code contains the text.

    Returns a list on purpose: zero matches means not found, and more than
    one means the name is ambiguous, so the agent must ask instead of guessing.
    """
    pattern = f"%{text}%"
    with connect() as conn:
        return conn.execute(
            """
            select id, code, name, client_name
            from projects
            where name ilike %s or code ilike %s
            order by name
            """,
            (pattern, pattern),
        ).fetchall()


def search_documents(project_id: int, query: str, limit: int = 5) -> list[dict]:
    """Keyword search over one project's documents, best matches first."""
    with connect() as conn:
        return conn.execute(
            """
            select d.id, d.title, d.kind, d.received_at::date as received,
                   ts_headline('english', d.raw_text, q,
                               'MaxFragments=2, MinWords=8, MaxWords=25') as snippet
            from documents d, websearch_to_tsquery('english', %s) q
            where d.project_id = %s and d.tsv @@ q
            order by ts_rank(d.tsv, q) desc
            limit %s
            """,
            (query, project_id, limit),
        ).fetchall()

def get_open_tasks(project_id: int) -> list[dict]:
    """Tasks that still need work: open or blocked, soonest due first."""
    with connect() as conn:
        return conn.execute(
            """
            select id, title, owner, due_date, status, blocked_reason
            from tasks
            where project_id = %s and status <> 'done'
            order by due_date nulls last, id
            """,
            (project_id,),
        ).fetchall()


def save_extracted_items(document_id: int, items) -> list[int]:
    """Store what the model extracted from a document. Returns the new item ids."""
    ids = []
    with connect() as conn:
        project_ids = {
            row["code"]: row["id"]
            for row in conn.execute("select id, code from projects").fetchall()
        }
        for item in items:
            row = conn.execute(
                """
                insert into extracted_items
                    (document_id, project_id, type, summary, due_date, owner, source_quote, confidence)
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (document_id, project_ids.get(item.project_code), item.type, item.summary,
                 item.due_date, item.owner, item.source_quote, item.confidence),
            ).fetchone()
            ids.append(row["id"])
    return ids


def get_recent_items(project_id: int, days: int = 30) -> list[dict]:
    """Items extracted from this project's documents in the last N days, newest first."""
    with connect() as conn:
        return conn.execute(
            """
            select i.id, i.type, i.summary, i.due_date, i.owner, i.source_quote,
                   d.title as document, d.received_at::date as received
            from extracted_items i
            join documents d on d.id = i.document_id
            where i.project_id = %s
              and d.received_at >= now() - make_interval(days => %s)
            order by d.received_at desc, i.id
            """,
            (project_id, days),
        ).fetchall()


def propose_change(project_id: int, kind: str, payload: dict, reason: str,
                   cited_item_ids: list[int]) -> int:
    """Put a change in the review queue. This is the ONLY way the agent changes anything."""
    with connect() as conn:
        row = conn.execute(
            """
            insert into proposed_changes (project_id, kind, payload, reason, cited_item_ids)
            values (%s, %s, %s, %s, %s)
            returning id
            """,
            (project_id, kind, Jsonb(payload, dumps=lambda o: json.dumps(o, default=str)),
             reason, cited_item_ids),
        ).fetchone()
    return row["id"]