from decimal import Decimal, InvalidOperation

from flask import abort, redirect, render_template, request, url_for

from .menu_db import (
    create_menu_item,
    delete_menu_item,
    get_menu_item,
    get_menu_items,
    update_menu_item,
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
        order_items = []
        return render_template("table_order.html", table=table, order_items=order_items)
