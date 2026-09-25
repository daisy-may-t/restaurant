import os
import tempfile
import unittest

from app import create_app
from app.db import get_db, init_db


class TablePageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.app.config["DATABASE"] = os.path.join(temp_dir.name, "restaurant.db")
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()

    def test_setup_seeds_tables_once(self):
        with self.app.app_context():
            db = get_db()
            self.assertEqual(
                [(row["id"], row["name"]) for row in db.execute(
                    "SELECT id, name FROM tables ORDER BY id"
                )],
                [(number, f"R{number}") for number in range(1, 11)]
                + [(number + 10, f"B{number}") for number in range(1, 11)],
            )
            db.execute("UPDATE tables SET name = 'Window' WHERE id = 1")
            db.commit()
            init_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM tables").fetchone()[0], 20)
            self.assertEqual(
                db.execute("SELECT name FROM tables WHERE id = 1").fetchone()[0],
                "Window",
            )
        response = self.client.get("/tables")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Window", response.data)
        self.assertNotIn(b"B10", response.data)
        self.assertIn(b"Available", response.data)
        self.assertEqual(response.data.count(b'<a class="table-card'), 10)
        bar_response = self.client.get("/tables?area=bar")
        self.assertIn(b"B10", bar_response.data)
        self.assertEqual(bar_response.data.count(b'<a class="table-card'), 10)

    def test_table_page_uses_database_name_and_rejects_unknown_id(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE tables SET name = 'Garden' WHERE id = 2")
            db.commit()
        response = self.client.get("/table/2")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Garden", response.data)
        self.assertEqual(self.client.get("/table/999").status_code, 404)
        self.assertEqual(self.client.get("/table/0").status_code, 404)

    def test_only_open_orders_mark_table_as_open(self):
        with self.app.app_context():
            db = get_db()
            db.execute("INSERT INTO orders (table_id, status) VALUES (1, 'open')")
            db.execute("INSERT INTO orders (table_id, status) VALUES (2, 'closed')")
            db.commit()
        response = self.client.get("/tables")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn('href="/table/1"', page)
        self.assertEqual(page.count('class="table-card table-card--open"'), 1)
        self.assertIn('0 items · &pound;0.00', page)

    def test_area_filter_and_saved_item_summaries(self):
        with self.app.app_context():
            db = get_db()
            restaurant_order = db.execute(
                "INSERT INTO orders (table_id, notes) VALUES (1, 'No nuts')"
            ).lastrowid
            bar_order = db.execute(
                "INSERT INTO orders (table_id) VALUES (11)"
            ).lastrowid
            closed_order = db.execute(
                "INSERT INTO orders (table_id, status) VALUES (2, 'closed')"
            ).lastrowid
            db.executemany(
                "INSERT INTO order_items "
                "(order_id, item_name, unit_price_pence, quantity) VALUES (?, ?, ?, ?)",
                [
                    (restaurant_order, "Soup", 250, 2),
                    (restaurant_order, "Tea", 150, 1),
                    (bar_order, "Water", 200, 1),
                    (closed_order, "Old meal", 9900, 1),
                ],
            )
            db.commit()

        restaurant = self.client.get("/tables").get_data(as_text=True)
        self.assertIn('3 items · &pound;6.50', restaurant)
        self.assertNotIn('href="/table/11"', restaurant)
        self.assertIn('href="/table/2"', restaurant)
        self.assertEqual(restaurant.count('class="table-card table-card--open"'), 1)
        self.assertIn('href="/tables?area=restaurant" aria-current="page"', restaurant)

        bar = self.client.get("/tables?area=bar").get_data(as_text=True)
        self.assertIn('1 item · &pound;2.00', bar)
        self.assertNotIn('href="/table/1"', bar)
        self.assertIn('href="/tables?area=bar" aria-current="page"', bar)
        self.assertEqual(self.client.get("/tables?area=other").status_code, 400)

if __name__ == "__main__":
    unittest.main()
