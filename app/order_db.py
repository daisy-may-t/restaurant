from .db import get_db


class MenuItemUnavailable(Exception):
    pass


class QuantityLimitReached(Exception):
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
    return {
        "id": order["id"],
        "items": [dict(item) for item in items],
        "total_pence": sum(item["unit_price_pence"] * item["quantity"] for item in items),
    }


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
        existing = db.execute("""
            SELECT id, quantity FROM order_items
            WHERE order_id = ? AND menu_item_id = ?
              AND item_name = ? AND unit_price_pence = ?
              AND notes IS NULL
            ORDER BY id LIMIT 1
        """, (order_id, menu_item_id, item["name"], item["price_pence"])).fetchone()
        if existing is not None:
            if existing["quantity"] >= 999:
                raise QuantityLimitReached
            db.execute(
                "UPDATE order_items SET quantity = quantity + 1 WHERE id = ?",
                (existing["id"],),
            )
            return
        db.execute("""
            INSERT INTO order_items
                (order_id, menu_item_id, item_name, unit_price_pence)
            VALUES (?, ?, ?, ?)
        """, (order_id, menu_item_id, item["name"], item["price_pence"]))


def change_quantity(table_id, item_id, quantity):
    db = get_db()
    with db:
        cursor = db.execute("""
            UPDATE order_items SET quantity = ?
            WHERE id = ? AND order_id IN (
                SELECT id FROM orders WHERE table_id = ? AND status = 'open'
            )
        """, (quantity, item_id, table_id))
    return cursor.rowcount > 0


def remove_item(table_id, item_id):
    db = get_db()
    with db:
        cursor = db.execute("""
            DELETE FROM order_items
            WHERE id = ? AND order_id IN (
                SELECT id FROM orders WHERE table_id = ? AND status = 'open'
            )
        """, (item_id, table_id))
    return cursor.rowcount > 0
