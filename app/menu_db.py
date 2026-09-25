from .db import get_db


def get_menu_items():
    rows = get_db().execute(
        "SELECT id, name, price FROM menu_items ORDER BY name ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_menu_item(item_id):
    row = get_db().execute(
        "SELECT id, name, price FROM menu_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    return dict(row) if row else None


def create_menu_item(name, price):
    cursor = get_db().execute(
        "INSERT INTO menu_items (name, price) VALUES (?, ?)",
        (name, price),
    )
    get_db().commit()
    return cursor.lastrowid


def update_menu_item(item_id, name, price):
    get_db().execute(
        "UPDATE menu_items SET name = ?, price = ? WHERE id = ?",
        (name, price, item_id),
    )
    get_db().commit()


def delete_menu_item(item_id):
    cursor = get_db().execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    get_db().commit()
    return cursor.rowcount > 0
