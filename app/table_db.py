from .db import get_db


def get_tables(area="restaurant", active_only=False):
    # Setup seeds restaurant tables as IDs 1-10 and bar tables as IDs 11-20.
    # Use IDs so a renamed table stays in its original area.
    filters = []
    parameters = []
    if area == "restaurant":
        filters.append("tables.id <= ?")
        parameters.append(10)
    elif area == "bar":
        filters.append("tables.id > ?")
        parameters.append(10)
    if active_only:
        filters.append("open_orders.id IS NOT NULL")
    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    rows = get_db().execute(f"""
        SELECT tables.id, tables.name,
               CASE WHEN tables.id <= 10 THEN 'restaurant' ELSE 'bar' END AS area,
               open_orders.id IS NOT NULL AS has_open_order,
               COALESCE(SUM(order_items.quantity), 0) AS item_count,
               COALESCE(SUM(order_items.quantity * order_items.unit_price_pence), 0)
                   AS total_pence
        FROM tables
        LEFT JOIN orders AS open_orders
            ON open_orders.table_id = tables.id AND open_orders.status = 'open'
        LEFT JOIN order_items ON order_items.order_id = open_orders.id
        {where_clause}
        GROUP BY tables.id, open_orders.id
        ORDER BY tables.id
    """, parameters).fetchall()
    return [dict(row) for row in rows]


def get_table(table_id):
    row = get_db().execute(
        "SELECT id, name FROM tables WHERE id = ?", (table_id,)
    ).fetchone()
    if row is None:
        return None
    table = dict(row)
    table["area"] = "restaurant" if table_id <= 10 else "bar"
    return table
