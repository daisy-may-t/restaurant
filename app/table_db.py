from .db import get_db


def get_tables(area="restaurant"):
    # Setup seeds restaurant tables as IDs 1-10 and bar tables as IDs 11-20.
    # Use IDs so a renamed table stays in its original area.
    first_id, last_id = (1, 10) if area == "restaurant" else (11, 20)
    rows = get_db().execute("""
        SELECT tables.id, tables.name,
               open_orders.id IS NOT NULL AS has_open_order,
               COALESCE(SUM(order_items.quantity), 0) AS item_count,
               COALESCE(SUM(order_items.quantity * order_items.unit_price_pence), 0)
                   AS total_pence
        FROM tables
        LEFT JOIN orders AS open_orders
            ON open_orders.table_id = tables.id AND open_orders.status = 'open'
        LEFT JOIN order_items ON order_items.order_id = open_orders.id
        WHERE tables.id BETWEEN ? AND ?
        GROUP BY tables.id, open_orders.id
        ORDER BY tables.id
    """, (first_id, last_id)).fetchall()
    return [dict(row) for row in rows]


def get_table(table_id):
    row = get_db().execute(
        "SELECT id, name FROM tables WHERE id = ?", (table_id,)
    ).fetchone()
    return dict(row) if row else None
