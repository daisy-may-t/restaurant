from decimal import Decimal, InvalidOperation

from flask import abort, redirect, render_template, request, url_for

from .menu_db import (
    create_menu_item,
    delete_menu_item,
    get_menu_item,
    get_menu_items,
    update_menu_item,
)
from .order_db import (
    MenuItemUnavailable,
    QuantityLimitReached,
    add_item,
    change_quantity,
    get_open_order,
    remove_item,
)
from .table_db import get_table, get_tables


def validate_menu_form(form):
    name = form.get("name", "").strip()
    price_text = form.get("price", "").strip()

    if not name or not price_text:
        return None, "Name and price are required."
    try:
        price = Decimal(price_text)
    except InvalidOperation:
        return None, "Price must be a valid number."
    if not price.is_finite() or price < 0 or price > 999.99:
        return None, "Price must be between 0 and 999.99 pounds."
    if price.as_tuple().exponent < -2:
        return None, "Price must have at most two decimal places."

    return (name, int(price * 100)), None


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("tables"))

    @app.route("/tables")
    def tables():
        return render_template("tables.html", tables=get_tables())

    @app.route("/menu", methods=["GET", "POST"])
    def menu():
        if request.method == "POST":
            values, error = validate_menu_form(request.form)
            if error:
                return render_template(
                    "menu.html", menu_items=get_menu_items(),
                    form_values=request.form, error=error,
                ), 400
            create_menu_item(*values)
            return redirect(url_for("menu"), code=303)
        return render_template("menu.html", menu_items=get_menu_items())

    @app.route("/menu/<int:item_id>/edit", methods=["GET", "POST"])
    def edit_menu_item(item_id):
        item = get_menu_item(item_id)
        if item is None:
            abort(404)
        if request.method == "POST":
            values, error = validate_menu_form(request.form)
            if error:
                return render_template(
                    "menu.html", menu_items=get_menu_items(), editing_item=item,
                    form_values=request.form, error=error,
                ), 400
            if not update_menu_item(item_id, *values):
                abort(404)
            return redirect(url_for("menu"), code=303)
        return render_template("menu.html", menu_items=get_menu_items(), editing_item=item)

    @app.route("/menu/<int:item_id>/delete", methods=["POST"])
    def delete_menu_item_route(item_id):
        if not delete_menu_item(item_id):
            abort(404)
        return redirect(url_for("menu"), code=303)

    @app.route("/table/<int:table_id>")
    def table_order(table_id):
        table = get_table(table_id)
        if table is None:
            abort(404)
        order = get_open_order(table_id)
        return render_template(
            "table_order.html", table=table,
            order_items=order["items"] if order else [],
            total_pence=order["total_pence"] if order else 0,
            menu_items=get_menu_items(),
        )

    @app.route("/table/<int:table_id>/items", methods=["POST"])
    def add_order_item(table_id):
        if get_table(table_id) is None:
            abort(404)
        menu_item_id = request.form.get("menu_item_id", type=int)
        if menu_item_id is None or menu_item_id <= 0:
            abort(400, description="Choose a menu item.")
        try:
            add_item(table_id, menu_item_id)
        except MenuItemUnavailable:
            abort(404, description="This menu item is no longer available.")
        except QuantityLimitReached:
            abort(400, description="This item is already at the maximum quantity of 999.")
        return redirect(url_for("table_order", table_id=table_id), code=303)

    @app.route("/table/<int:table_id>/items/<int:item_id>/quantity", methods=["POST"])
    def update_order_item_quantity(table_id, item_id):
        quantity = request.form.get("quantity", type=int)
        if quantity is None or not 1 <= quantity <= 999:
            abort(400, description="Quantity must be between 1 and 999.")
        if not change_quantity(table_id, item_id, quantity):
            abort(404)
        return redirect(url_for("table_order", table_id=table_id), code=303)

    @app.route("/table/<int:table_id>/items/<int:item_id>/remove", methods=["POST"])
    def remove_order_item(table_id, item_id):
        if not remove_item(table_id, item_id):
            abort(404)
        return redirect(url_for("table_order", table_id=table_id), code=303)
