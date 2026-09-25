from .db import get_db


def get_menu_items():
    rows = get_db().execute(
        "SELECT id, name, price_pence FROM menu_items ORDER BY name, id"
    ).fetchall()
    return [dict(row) for row in rows]


def get_menu_item(item_id):
    row = get_db().execute(
        "SELECT id, name, price_pence FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    return dict(row) if row else None


def create_menu_item(name, price_pence):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO menu_items (name, price_pence) VALUES (?, ?)",
        (name, price_pence),
    )
    db.commit()
    return cursor.lastrowid


def update_menu_item(item_id, name, price_pence):
    db = get_db()
    cursor = db.execute(
        "UPDATE menu_items SET name = ?, price_pence = ? WHERE id = ?",
        (name, price_pence, item_id),
    )
    db.commit()
    return cursor.rowcount > 0


def delete_menu_item(item_id):
    db = get_db()
    cursor = db.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    db.commit()
    return cursor.rowcount > 0
