from .db import get_db


class MenuItemUnavailable(Exception):
    pass


def get_open_order(table_id):
    db = get_db()
    order = db.execute(
        "SELECT id FROM orders WHERE table_id = ? AND status = 'open'",
        (table_id,),
    ).fetchone()
    if order is None:
        return None
    items = db.execute("""
        SELECT id, item_name, unit_price_pence, quantity
        FROM order_items WHERE order_id = ? ORDER BY id
    """, (order["id"],)).fetchall()
    return {"id": order["id"], "items": [dict(item) for item in items]}


def add_item(table_id, menu_item_id):
    db = get_db()
    with db:
        # The partial unique index makes another device reuse the open order.
        db.execute("""
            INSERT INTO orders (table_id) VALUES (?)
            ON CONFLICT(table_id) WHERE status = 'open' DO NOTHING
        """, (table_id,))
        order_id = db.execute(
            "SELECT id FROM orders WHERE table_id = ? AND status = 'open'",
            (table_id,),
        ).fetchone()["id"]
        item = db.execute(
            "SELECT name, price_pence FROM menu_items WHERE id = ?",
            (menu_item_id,),
        ).fetchone()
        if item is None:
            raise MenuItemUnavailable
        db.execute("""
            INSERT INTO order_items
                (order_id, menu_item_id, item_name, unit_price_pence)
            VALUES (?, ?, ?, ?)
        """, (order_id, menu_item_id, item["name"], item["price_pence"]))
