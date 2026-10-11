from app.db import connect


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