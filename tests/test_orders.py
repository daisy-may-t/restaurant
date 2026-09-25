import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app import create_app
from app.db import get_db, init_db
from app.menu_db import create_menu_item, update_menu_item
from app.order_db import add_item


class FirstOrderItemTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.app.config["DATABASE"] = os.path.join(
            temporary_directory.name, "restaurant.db"
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            init_db()
            self.item_id = create_menu_item("Soup", 525)

    def add_from_browser(self, table_id, item_id):
        self.client.get(f"/table/{table_id}")
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        return self.client.post(
            f"/table/{table_id}/items",
            data={"menu_item_id": str(item_id), "csrf_token": token},
        )

    def test_first_item_creates_persistent_order(self):
        self.assertEqual(self.client.get("/table/1").status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
        self.assertEqual(self.add_from_browser(1, self.item_id).status_code, 303)
        self.assertIn(b"Soup", self.client.get("/table/1").data)
        self.assertIn(b"5.25", self.client.get("/table/1").data)
        self.assertIn(b"Open order", self.client.get("/tables").data)

        another_client = self.app.test_client()
        self.assertIn(b"Soup", another_client.get("/table/1").data)
        self.assertIn(b"No items yet", another_client.get("/table/2").data)
        restarted_app = create_app()
        restarted_app.config["TESTING"] = True
        restarted_app.config["DATABASE"] = self.app.config["DATABASE"]
        self.assertIn(b"Soup", restarted_app.test_client().get("/table/1").data)
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 1)

    def test_more_items_reuse_order_and_keep_price_snapshot(self):
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            update_menu_item(self.item_id, "New Soup", 650)
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)
            rows = db.execute(
                "SELECT item_name, unit_price_pence FROM order_items ORDER BY id"
            ).fetchall()
            self.assertEqual([tuple(row) for row in rows],
                             [("Soup", 525), ("New Soup", 650)])

    def test_invalid_item_or_table_creates_no_order(self):
        self.assertEqual(self.add_from_browser(1, 999).status_code, 404)
        self.assertEqual(self.add_from_browser(999, self.item_id).status_code, 404)
        self.assertEqual(self.add_from_browser(1, 0).status_code, 400)
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 0)

    def test_two_writers_share_one_open_order(self):
        barrier = Barrier(2)

        def add_from_device():
            with self.app.app_context():
                barrier.wait()
                add_item(1, self.item_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(add_from_device) for _ in range(2)]
            for future in futures:
                future.result()

        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
