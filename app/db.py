from contextlib import closing
import os
import sqlite3

from flask import current_app, g


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "db", "restaurant.db")


def connect_db():
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(reset=False):
    db_path = current_app.config["DATABASE"]
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with closing(connect_db()) as conn:
        with conn:
            if reset:
                for table in ("order_items", "orders", "tables", "menu_items"):
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
            elif conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'menu_items'"
            ).fetchone():
                columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(menu_items)")
                }
                if "price_pence" not in columns:
                    raise RuntimeError(
                        "Old database schema found. Back up the database, then run "
                        "'flask --app app setup-db --reset' to discard test data."
                    )

            conn.executescript("""
                CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                    price_pence INTEGER NOT NULL
                        CHECK (price_pence BETWEEN 0 AND 99999)
                );
                CREATE TABLE IF NOT EXISTS tables (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    table_id INTEGER NOT NULL REFERENCES tables(id) ON DELETE RESTRICT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    status TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'closed'))
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_open_order_per_table
                    ON orders(table_id) WHERE status = 'open';
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY,
                    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE SET NULL,
                    item_name TEXT NOT NULL CHECK (length(trim(item_name)) > 0),
                    unit_price_pence INTEGER NOT NULL CHECK (unit_price_pence >= 0),
                    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
                    notes TEXT
                );
            """)
            if conn.execute("SELECT COUNT(*) FROM tables").fetchone()[0] == 0:
                conn.executemany(
                    "INSERT INTO tables (name) VALUES (?)",
                    [(f"{area}{number}",) for area in ("R", "B")
                     for number in range(1, 11)],
                )
