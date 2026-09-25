from datetime import datetime


def pounds(pence):
    return f"\u00a3{pence // 100}.{pence % 100:02d}"


def format_ticket(table_name, order, printed_at=None):
    """Build the text shown in the ticket preview from saved order values."""
    if printed_at is None:
        printed_at = datetime.now().astimezone()
    lines = [
        f"TABLE {table_name}",
        printed_at.strftime("%d/%m/%Y %H:%M"),
        "-" * 32,
    ]
    for item in order["items"]:
        line_total = item["unit_price_pence"] * item["quantity"]
        lines.append(f"{item['quantity']} x {item['item_name']}")
        lines.append(f"  {pounds(item['unit_price_pence'])} each    {pounds(line_total)}")
    lines.extend(["-" * 32, f"TOTAL {pounds(order['total_pence'])}"])
    if order["notes"]:
        lines.extend(["-" * 32, "NOTES", order["notes"]])
    return "\n".join(lines)
