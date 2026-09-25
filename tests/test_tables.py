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
        self.assertIn(b"B10", response.data)
        self.assertIn(b"No order", response.data)

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
        self.assertEqual(page.count('<small>Open order</small>'), 1)

if __name__ == "__main__":
    unittest.main()
