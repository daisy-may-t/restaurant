import os
import tempfile
import unittest

from app import create_app


class MenuCrudTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.app.config["DATABASE"] = os.path.join(temp_dir.name, "restaurant.db")
        self.client = self.app.test_client()

        with self.app.app_context():
            from app.db import init_db

            init_db()

    def test_menu_crud(self):
        response = self.client.get("/menu")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Menu", response.data)

        response = self.client.post(
            "/menu",
            data={"name": "Burger", "price": "12.50"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Burger", response.data)

        with self.app.app_context():
            from app.db import get_db

            item = get_db().execute(
                "SELECT * FROM menu_items WHERE name = ?",
                ("Burger",),
            ).fetchone()
            self.assertIsNotNone(item)
            item_id = item["id"]

        response = self.client.post(
            f"/menu/{item_id}/edit",
            data={"name": "Burger Deluxe", "price": "15.75"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Burger Deluxe", response.data)

        response = self.client.post(
            f"/menu/{item_id}/delete",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Burger Deluxe", response.data)

        with self.app.app_context():
            from app.db import get_db

            count = get_db().execute("SELECT COUNT(*) FROM menu_items").fetchone()[0]
            self.assertEqual(count, 0)

    def test_invalid_prices_do_not_change_database(self):
        self.client.post("/menu", data={"name": "Original", "price": "2.50"})
        for path in ("/menu", "/menu/1/edit"):
            for price in ("", "abc", "-1", "NaN", "Infinity", "1e999", "1.234"):
                with self.subTest(path=path, price=price):
                    response = self.client.post(path, data={"name": "Attempt", "price": price})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(b'value="Attempt"', response.data)
        with self.app.app_context():
            from app.menu_db import get_menu_items
            self.assertEqual(get_menu_items(), [{"id": 1, "name": "Original", "price": 2.5}])

    def test_name_required_and_zero_price_allowed(self):
        response = self.client.post("/menu", data={"name": "  ", "price": "1"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/menu", data={"name": " Water ", "price": "0"})
        self.assertEqual(response.status_code, 303)
        with self.app.app_context():
            from app.menu_db import get_menu_items
            self.assertEqual(get_menu_items()[0]["name"], "Water")

    def test_missing_items(self):
        self.assertEqual(self.client.get("/menu/999/edit").status_code, 404)
        self.assertEqual(self.client.post("/menu/999/edit").status_code, 404)
        self.assertEqual(self.client.post("/menu/999/delete").status_code, 404)

    def test_get_does_not_modify_items(self):
        self.client.post("/menu", data={"name": "Soup", "price": "5.25"})
        response = self.client.get("/menu/1/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="Soup"', response.data)
        self.assertEqual(self.client.get("/menu/1/delete").status_code, 405)
        with self.app.app_context():
            from app.menu_db import get_menu_item
            self.assertEqual(get_menu_item(1)["price"], 5.25)


if __name__ == "__main__":
    unittest.main()
