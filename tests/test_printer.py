import os
import tempfile
import unittest
from datetime import datetime

from app import create_app
from app.db import init_db
from app.menu_db import create_menu_item, update_menu_item
from app.order_db import add_item, save_notes
from app.printer import format_ticket


class TicketTests(unittest.TestCase):
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

    def test_ticket_uses_saved_values_and_exact_pence(self):
        order = {
            "items": [
                {"item_name": "Soup", "unit_price_pence": 525, "quantity": 2},
                {"item_name": "Tea", "unit_price_pence": 200, "quantity": 1},
            ],
            "total_pence": 1250,
            "notes": "No peanuts\nExtra sauce",
        }
        ticket = format_ticket("R1", order, datetime(2026, 9, 25, 18, 30))
        self.assertIn("TABLE R1\n25/09/2026 18:30", ticket)
        self.assertIn("2 x Soup\n  £5.25 each    £10.50", ticket)
        self.assertIn("TOTAL £12.50", ticket)
        self.assertIn("NOTES\nNo peanuts\nExtra sauce", ticket)

    def test_preview_reads_order_without_changing_it(self):
        with self.app.app_context():
            add_item(1, self.item_id)
            save_notes(1, "No <nuts>")
            update_menu_item(self.item_id, "New Soup", 650)
        response = self.client.get("/table/1/ticket")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Soup", response.data)
        self.assertIn(b"5.25", response.data)
        self.assertNotIn(b"New Soup", response.data)
        self.assertIn(b"No &lt;nuts&gt;", response.data)
        self.assertIn(b"window.print()", response.data)
        self.assertIn(b"Preview ticket", self.client.get("/table/1").data)

    def test_preview_requires_an_order_with_items(self):
        self.assertEqual(self.client.get("/table/999/ticket").status_code, 404)
        self.assertEqual(self.client.get("/table/1/ticket").status_code, 404)
        with self.app.app_context():
            save_notes(1, "No dairy")
        self.assertEqual(self.client.get("/table/1/ticket").status_code, 400)


if __name__ == "__main__":
    unittest.main()
