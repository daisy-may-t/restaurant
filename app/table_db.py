from .db import get_db


def get_tables():
    rows = get_db().execute("""
        SELECT tables.id, tables.name,
               EXISTS (
                   SELECT 1 FROM orders
                   WHERE orders.table_id = tables.id AND orders.status = 'open'
               ) AS has_open_order
        FROM tables
        ORDER BY tables.id
    """).fetchall()
    return [dict(row) for row in rows]


def get_table(table_id):
    row = get_db().execute(
        "SELECT id, name FROM tables WHERE id = ?", (table_id,)
    ).fetchone()
    return dict(row) if row else None
