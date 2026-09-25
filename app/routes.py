from flask import redirect, render_template, url_for


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("tables"))

    @app.route("/tables")
    def tables():
        tables_data = [
            {"id": 1, "name": "Table 1"},
            {"id": 2, "name": "Table 2"},
            {"id": 3, "name": "Table 3"},
        ]
        return render_template("tables.html", tables=tables_data)

    @app.route("/menu")
    def menu():
        menu_items = [
            {"id": 1, "name": "Burger", "price": 12.50},
            {"id": 2, "name": "Fries", "price": 4.50},
            {"id": 3, "name": "Soft Drink", "price": 2.75},
        ]
        return render_template("menu.html", menu_items=menu_items)

    @app.route("/table/<int:table_id>")
    def table_order(table_id):
        table = {"id": table_id, "name": f"Table {table_id}"}
        order_items = []
        return render_template("table_order.html", table=table, order_items=order_items)
