from contextlib import closing
import os
import sqlite3
import tempfile
import unittest

from app import create_app
from app.db import get_db, init_db
from app.menu_db import create_menu_item, get_menu_item, get_menu_items, update_menu_item


class MenuCrudTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.app.config["DATABASE"] = os.path.join(temp_dir.name, "restaurant.db")
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()
        self.client.get("/menu")

    def post(self, path, data=None, **kwargs):
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        return self.client.post(
            path, data={**(data or {}), "csrf_token": token}, **kwargs
        )

    def test_menu_crud(self):
        response = self.post("/menu", {
            "name": "Burger", "price": "12.50", "category": "Grill"
        })
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            item = get_menu_items()[0]
            self.assertEqual(item["price_pence"], 1250)
            self.assertEqual(item["category"], "Grill")
        response = self.client.get("/menu")
        self.assertIn(b"Burger", response.data)
        self.assertIn(b"12.50", response.data)
        self.assertIn(b'<option value="Grill"></option>', response.data)

        item_id = item["id"]
        response = self.client.get(f"/menu/{item_id}/edit")
        self.assertIn(b'value="12.50"', response.data)
        self.assertIn(b'value="Grill"', response.data)
        response = self.post(
            f"/menu/{item_id}/edit", {
                "name": "Burger Deluxe", "price": "15.75", "category": " Specials "
            }
        )
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            self.assertEqual(get_menu_item(item_id)["price_pence"], 1575)
            self.assertEqual(get_menu_item(item_id)["name"], "Burger Deluxe")
            self.assertEqual(get_menu_item(item_id)["category"], "Specials")
        self.assertIn(b"15.75", self.client.get("/menu").data)

        response = self.post(f"/menu/{item_id}/delete")
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            self.assertIsNone(get_menu_item(item_id))

    def test_invalid_prices_do_not_change_database(self):
        self.post("/menu", {"name": "Original", "price": "2.50"})
        for path in ("/menu", "/menu/1/edit"):
            for price in ("", "abc", "-1", "NaN", "Infinity", "1e999", "1.234", "2.500", "1000"):
                with self.subTest(path=path, price=price):
                    response = self.post(path, {"name": "Attempt", "price": price})
                    self.assertEqual(response.status_code, 400)
                    if price == "abc" and path == "/menu":
                        self.assertIn(b'value="Attempt"', response.data)
        with self.app.app_context():
            self.assertEqual(get_menu_items(), [
                {"id": 1, "name": "Original", "price_pence": 250,
                 "category": "Other"}
            ])

    def test_category_storage_and_existing_database_migration(self):
        with self.app.app_context():
            item_id = create_menu_item("Green curry", 950, "Curry")
            self.assertEqual(get_menu_item(item_id)["category"], "Curry")
            update_menu_item(item_id, "Green curry", 975)
            self.assertEqual(get_menu_item(item_id)["category"], "Curry")
            update_menu_item(item_id, "Green curry", 975, "Chef's picks")
            self.assertEqual(get_menu_item(item_id)["category"], "Chef's picks")

        old_path = os.path.join(os.path.dirname(self.app.config["DATABASE"]), "existing.db")
        with closing(sqlite3.connect(old_path)) as old_db:
            old_db.execute("""CREATE TABLE menu_items (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                price_pence INTEGER NOT NULL)""")
            old_db.execute("INSERT INTO menu_items (name, price_pence) VALUES ('Rice', 300)")
            old_db.commit()
        self.app.config["DATABASE"] = old_path
        with self.app.app_context():
            init_db()
            init_db()
            self.assertEqual(get_menu_items()[0]["category"], "Other")

    def test_invalid_category_keeps_existing_item_and_form_value(self):
        self.post("/menu", {"name": "Rice", "price": "3.00", "category": "Sides"})
        for path in ("/menu", "/menu/1/edit"):
            for category in ("   ", "X" * 61):
                with self.subTest(path=path, category=category):
                    response = self.post(path, {
                        "name": "Changed", "price": "4.00", "category": category
                    })
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b"Category must be between 1 and 60 characters", response.data)
                    self.assertIn(f'value="{category}"'.encode(), response.data)
        with self.app.app_context():
            self.assertEqual(get_menu_item(1)["category"], "Sides")
            self.assertEqual(len(get_menu_items()), 1)

    def test_category_tabs_filter_and_preserve_selection(self):
        response = self.post("/menu", {
            "name": "Green curry", "price": "9", "category": "Curry"
        })
        self.assertIn("category=Curry", response.headers["Location"])
        self.post("/menu", {"name": "Rice", "price": "3", "category": "Other"})

        page = self.client.get("/menu?category=Curry").data
        self.assertIn(b'aria-label="Menu categories"', page)
        self.assertIn(b'href="/menu?category=Curry" aria-current="page"', page)
        self.assertIn(b"Green curry", page)
        self.assertNotIn(b'data-label="Name">Rice', page)
        self.assertIn(b'/menu/1/edit?category=Curry', page)
        self.assertIn(b'/menu/1/delete?category=Curry', page)
        self.assertIn(b'data-label="Name">Rice', self.client.get("/menu").data)
        self.assertIn(b'data-label="Name">Rice',
                      self.client.get("/menu?category=Missing").data)

        response = self.post("/menu/1/edit?category=Curry", {
            "name": "Green curry", "price": "9", "category": "Special"
        })
        self.assertIn("category=Special", response.headers["Location"])
        response = self.post("/menu/1/delete?category=Special")
        self.assertEqual(response.headers["Location"], "/menu")

    def test_zero_price_and_trimmed_name(self):
        self.post("/menu", {"name": " Water ", "price": "0"})
        self.post("/menu", {"name": "Special", "price": "999.99"})
        with self.app.app_context():
            self.assertEqual(
                [(item["name"], item["price_pence"]) for item in get_menu_items()],
                [("Special", 99999), ("Water", 0)],
            )
        self.assertEqual(
            self.post("/menu", {"name": "  ", "price": "1"}).status_code, 400
        )

    def test_csrf_required_for_changes(self):
        self.assertEqual(
            self.client.post("/menu", data={"name": "Soup", "price": "5"}).status_code,
            400,
        )
        self.assertEqual(self.client.post("/menu/1/delete").status_code, 400)
        self.assertEqual(self.client.post("/menu/1/edit").status_code, 400)
        self.assertEqual(
            self.client.post("/menu", data={
                "name": "Soup", "price": "5", "csrf_token": "wrong"
            }).status_code,
            400,
        )
        self.assertIn(b'name="csrf_token"', self.client.get("/menu").data)
        with self.app.app_context():
            self.assertEqual(get_menu_items(), [])

    def test_missing_items_and_delete_requires_post(self):
        self.assertEqual(self.client.get("/menu/999/edit").status_code, 404)
        self.assertEqual(self.post("/menu/999/edit", {"name": "X", "price": "1"}).status_code, 404)
        self.assertEqual(self.post("/menu/999/delete").status_code, 404)
        self.post("/menu", {"name": "Soup", "price": "5"})
        self.assertEqual(self.client.get("/menu/1/delete").status_code, 405)
        with self.app.app_context():
            self.assertEqual(get_menu_item(1)["name"], "Soup")

    def test_constraints_and_menu_deletion_keep_order_snapshot(self):
        self.post("/menu", {"name": "Soup", "price": "5.25"})
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO menu_items (name, price_pence) VALUES (?, ?)",
                           ("Bad", -1))
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO menu_items (name, price_pence) VALUES (?, ?)",
                           ("Too expensive", 100000))
            db.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO orders (table_id) VALUES (999)")
            db.rollback()
            db.execute("INSERT INTO orders (id, table_id) VALUES (1, 1)")
            db.execute("""INSERT INTO order_items
                (order_id, menu_item_id, item_name, unit_price_pence, quantity)
                VALUES (1, 1, 'Soup', 525, 2)""")
            db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("""INSERT INTO order_items
                    (order_id, item_name, unit_price_pence, quantity)
                    VALUES (1, 'Bad', 100, 0)""")
            db.rollback()
        self.assertEqual(self.post("/menu/1/delete").status_code, 303)
        with self.app.app_context():
            row = get_db().execute(
                "SELECT menu_item_id, item_name, unit_price_pence FROM order_items"
            ).fetchone()
            self.assertEqual(tuple(row), (None, "Soup", 525))

    def test_reset_command_replaces_old_schema(self):
        legacy_path = os.path.join(
            os.path.dirname(self.app.config["DATABASE"]), "legacy.db"
        )
        with closing(sqlite3.connect(legacy_path)) as old_db:
            old_db.execute("CREATE TABLE menu_items (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
            old_db.execute("INSERT INTO menu_items (name, price) VALUES ('Old', 1.2)")
            old_db.commit()
        self.app.config["DATABASE"] = legacy_path
        with self.app.app_context():
            with self.assertRaisesRegex(RuntimeError, "Old database schema"):
                init_db()
            init_db(reset=True)
            self.assertEqual(get_menu_items(), [])


if __name__ == "__main__":
    unittest.main()
