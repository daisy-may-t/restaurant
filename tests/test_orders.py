import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import quote

from app import create_app
from app.db import get_db, init_db
from app.menu_db import create_menu_item, update_menu_item
from app.order_db import add_item, get_open_order, save_notes


class OrderFlowTests(unittest.TestCase):
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

    def post_order_action(self, path, data=None):
        self.client.get("/table/1")
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        return self.client.post(path, data={**(data or {}), "csrf_token": token})

    def test_first_item_creates_persistent_order(self):
        self.assertEqual(self.client.get("/table/1").status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
        self.assertEqual(self.add_from_browser(1, self.item_id).status_code, 303)
        self.assertIn(b"Soup", self.client.get("/table/1").data)
        self.assertIn(b"5.25", self.client.get("/table/1").data)

        another_client = self.app.test_client()
        self.assertIn(b"Soup", another_client.get("/table/1").data)
        restarted_app = create_app()
        restarted_app.config["TESTING"] = True
        restarted_app.config["DATABASE"] = self.app.config["DATABASE"]
        self.assertIn(b"Soup", restarted_app.test_client().get("/table/1").data)
        with self.app.app_context():
            db = get_db()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 1)

    def test_add_item_categories_filter_and_keep_order_snapshot(self):
        long_category = "Chef's very special noodle dishes"
        with self.app.app_context():
            noodle_id = create_menu_item("Pad Thai", 1095, long_category)
        selected_url = f"/table/1?category={quote(long_category)}"
        page = self.client.get(selected_url).get_data(as_text=True)
        self.assertIn('aria-label="Menu categories"', page)
        self.assertIn(f'name="menu_item_id" required', page)
        self.assertIn(f'<option value="{noodle_id}">Pad Thai', page)
        self.assertNotIn(f'<option value="{self.item_id}">Soup', page)
        self.assertIn("Chef&#39;s very special noodle dishes", page)

        self.client.get("/table/1")
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        response = self.client.post(
            f"/table/1/items?category={quote(long_category)}",
            data={"menu_item_id": noodle_id, "csrf_token": token},
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("category=Chef", response.headers["Location"])
        with self.app.app_context():
            order = get_open_order(1)
            self.assertEqual(order["items"][0]["item_name"], "Pad Thai")
            self.assertEqual(order["total_pence"], 1095)
        self.assertIn(b"Pad Thai", self.client.get("/table/1").data)
        self.assertIn(b"Soup", self.client.get("/table/1").data)

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
            lines = db.execute("SELECT quantity FROM order_items").fetchall()
            self.assertEqual([row["quantity"] for row in lines], [2])

    def test_quantity_change_and_removal_recalculate_total(self):
        self.add_from_browser(1, self.item_id)
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            tea_id = create_menu_item("Tea", 200)
        self.add_from_browser(1, tea_id)
        with self.app.app_context():
            order = get_open_order(1)
            first_id, second_id = [item["id"] for item in order["items"]]
            self.assertEqual(order["items"][0]["quantity"], 2)
            self.assertEqual(order["total_pence"], 1250)

        response = self.post_order_action(
            f"/table/1/items/{first_id}/quantity", {"quantity": "3"}
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn(b"17.75", self.client.get("/table/1").data)
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["total_pence"], 1775)

        response = self.post_order_action(f"/table/1/items/{second_id}/remove")
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["total_pence"], 1575)

        self.post_order_action(f"/table/1/items/{first_id}/remove")
        with self.app.app_context():
            order = get_open_order(1)
            self.assertIsNotNone(order)
            self.assertEqual(order["items"], [])
            self.assertEqual(order["total_pence"], 0)

    def test_order_controls_and_area_back_link(self):
        self.add_from_browser(11, self.item_id)
        page = self.client.get("/table/11").get_data(as_text=True)
        self.assertIn('href="/tables?area=bar"', page)
        self.assertIn('aria-label="Increase quantity of Soup"', page)
        self.assertIn('aria-label="Decrease quantity of Soup" disabled', page)
        self.assertIn('aria-label="Remove Soup"', page)
        self.assertIn('id="notes-form"', page)
        self.assertIn('id="notes-warning"', page)
        self.assertIn('Preview ticket', page)

    def test_quantity_buttons_use_current_saved_value_and_respect_limits(self):
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            item_id = get_open_order(1)["items"][0]["id"]
        path = f"/table/1/items/{item_id}/quantity"

        second_client = self.app.test_client()
        second_client.get("/table/1")
        with second_client.session_transaction() as session:
            second_token = session["csrf_token"]
        self.client.get("/table/1")
        self.assertEqual(
            self.post_order_action(path, {"change": "1"}).status_code, 303
        )
        self.assertEqual(
            second_client.post(path, data={"change": "1", "csrf_token": second_token}).status_code,
            303,
        )
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["items"][0]["quantity"], 3)

        self.assertEqual(
            self.post_order_action(path, {"change": "-1"}).status_code, 303
        )
        self.assertEqual(
            self.post_order_action(path, {"change": "0"}).status_code, 400
        )
        self.post_order_action(path, {"quantity": "999"})
        self.assertIn('aria-label="Increase quantity of Soup" disabled',
                      self.client.get("/table/1").get_data(as_text=True))
        self.assertEqual(
            self.post_order_action(path, {"change": "1"}).status_code, 400
        )
        self.post_order_action(path, {"quantity": "1"})
        self.assertEqual(
            self.post_order_action(path, {"change": "-1"}).status_code, 400
        )
        self.assertEqual(
            self.post_order_action("/table/1/items/999/quantity", {"change": "1"}).status_code,
            404,
        )
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["items"][0]["quantity"], 1)

    def test_adding_beyond_999_does_not_create_another_line(self):
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            item_id = get_open_order(1)["items"][0]["id"]
        self.assertEqual(
            self.post_order_action(
                f"/table/1/items/{item_id}/quantity", {"quantity": "998"}
            ).status_code,
            303,
        )
        self.assertEqual(self.add_from_browser(1, self.item_id).status_code, 303)
        response = self.add_from_browser(1, self.item_id)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"maximum quantity of 999", response.data)
        with self.app.app_context():
            order = get_open_order(1)
            self.assertEqual(len(order["items"]), 1)
            self.assertEqual(order["items"][0]["quantity"], 999)
            self.assertEqual(order["total_pence"], 999 * 525)

    def test_notes_persist_across_devices_and_can_be_cleared(self):
        self.assertIn(b'name="notes"', self.client.get("/table/1").data)
        response = self.post_order_action(
            "/table/1/notes", {"notes": "  No peanuts\nExtra sauce  "}
        )
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            order = get_open_order(1)
            self.assertEqual(order["notes"], "No peanuts\nExtra sauce")
            self.assertEqual(order["items"], [])
            order_id = order["id"]

        notes_only_page = self.client.get("/table/1").get_data(as_text=True)
        self.assertIn("Open order · 0 items", notes_only_page)
        self.assertIn("Save notes", notes_only_page)

        another_client = self.app.test_client()
        self.assertIn(b"No peanuts\nExtra sauce", another_client.get("/table/1").data)
        self.assertIn(b"Open order", another_client.get("/tables").data)
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            order = get_open_order(1)
            self.assertEqual(order["id"], order_id)
            self.assertEqual(order["notes"], "No peanuts\nExtra sauce")
            self.assertEqual(len(order["items"]), 1)
        self.assertEqual(
            self.post_order_action("/table/1/notes", {"notes": ""}).status_code,
            303,
        )
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["notes"], "")

    def test_blank_notes_do_not_create_order_and_notes_have_size_limit(self):
        self.assertEqual(
            self.post_order_action("/table/1/notes", {"notes": "   "}).status_code,
            303,
        )
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM orders").fetchone()[0], 0)
        self.assertEqual(
            self.post_order_action("/table/1/notes", {"notes": "x" * 2001}).status_code,
            400,
        )
        self.assertEqual(
            self.post_order_action("/table/999/notes", {"notes": "Wrong table"}).status_code,
            404,
        )
        with self.app.app_context():
            self.assertIsNone(get_open_order(1))

    def test_notes_and_first_item_started_together_share_one_order(self):
        barrier = Barrier(2)

        def save_note():
            with self.app.app_context():
                barrier.wait()
                save_notes(1, "No nuts")

        def add_food():
            with self.app.app_context():
                barrier.wait()
                add_item(1, self.item_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(save_note), pool.submit(add_food)]
            for future in futures:
                future.result()

        with self.app.app_context():
            order = get_open_order(1)
            self.assertEqual(order["notes"], "No nuts")
            self.assertEqual(len(order["items"]), 1)
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM orders").fetchone()[0], 1)

    def test_reset_closes_order_and_next_item_starts_fresh(self):
        self.add_from_browser(1, self.item_id)
        self.post_order_action("/table/1/notes", {"notes": "No peanuts"})
        with self.app.app_context():
            old_order = get_open_order(1)
            old_item_id = old_order["items"][0]["id"]
        self.assertIn(b"Reset order", self.client.get("/table/1").data)
        self.assertEqual(self.client.get("/table/1/reset").status_code, 405)

        response = self.post_order_action("/table/1/reset")
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            self.assertIsNone(get_open_order(1))
        self.assertNotIn(b"Reset order", self.client.get("/table/1").data)
        self.assertNotIn(b"Open order", self.client.get("/tables").data)
        self.assertEqual(
            self.post_order_action(
                f"/table/1/items/{old_item_id}/quantity", {"quantity": "2"}
            ).status_code,
            404,
        )

        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            db = get_db()
            current = get_open_order(1)
            self.assertNotEqual(current["id"], old_order["id"])
            self.assertEqual(current["notes"], "")
            self.assertEqual(len(current["items"]), 1)
            rows = db.execute(
                "SELECT id, status, notes FROM orders WHERE table_id = 1 ORDER BY id"
            ).fetchall()
            self.assertEqual([row["status"] for row in rows], ["closed", "open"])
            self.assertEqual(rows[0]["notes"], "No peanuts")
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM order_items WHERE order_id = ?",
                (old_order["id"],),
            ).fetchone()[0], 1)

    def test_reset_handles_notes_only_order_and_requires_open_order(self):
        self.assertEqual(self.post_order_action("/table/1/reset").status_code, 404)
        self.post_order_action("/table/1/notes", {"notes": "Dairy allergy"})
        self.assertEqual(self.post_order_action("/table/1/reset").status_code, 303)
        self.assertEqual(self.post_order_action("/table/1/reset").status_code, 404)
        with self.app.app_context():
            self.assertIsNone(get_open_order(1))
            row = get_db().execute(
                "SELECT status, notes FROM orders WHERE table_id = 1"
            ).fetchone()
            self.assertEqual(tuple(row), ("closed", "Dairy allergy"))

    def test_invalid_or_other_tables_lines_cannot_be_changed(self):
        self.add_from_browser(1, self.item_id)
        with self.app.app_context():
            item_id = get_open_order(1)["items"][0]["id"]
        quantity_path = f"/table/1/items/{item_id}/quantity"
        for value in ("", "0", "-1", "abc", "1000"):
            with self.subTest(quantity=value):
                self.assertEqual(
                    self.post_order_action(quantity_path, {"quantity": value}).status_code,
                    400,
                )
        self.assertEqual(
            self.post_order_action(
                f"/table/2/items/{item_id}/quantity", {"quantity": "4"}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.post_order_action(f"/table/2/items/{item_id}/remove").status_code,
            404,
        )
        self.assertEqual(
            self.post_order_action("/table/1/items/999/remove").status_code, 404
        )
        with self.app.app_context():
            self.assertEqual(get_open_order(1)["items"][0]["quantity"], 1)
            self.assertEqual(get_open_order(1)["total_pence"], 525)


if __name__ == "__main__":
    unittest.main()
