class PrinterService:
    """Placeholder printer service for the MVP."""

    def print_order(self, table_name, order_items, notes=""):
        print(f"PRINTING ORDER FOR {table_name.upper()}")
        print("-" * 20)
        for item in order_items:
            print(f"{item['name']} x{item['quantity']} - £{item['price'] * item['quantity']:.2f}")
        if notes:
            print(f"Notes: {notes}")
        print("-" * 20)
        print("ORDER COMPLETE")
