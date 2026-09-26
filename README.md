# Restaurant App

A simple local-first restaurant ordering app for tracking menu items, tables, and orders.

## Requirements

- Python 3.10+
- A host computer and phones on the same local network

## Local setup

1. Open a terminal in the project folder.
2. Create a virtual environment:
   python -m venv .venv
3. Activate it:
   - Windows PowerShell: .\.venv\Scripts\Activate.ps1
   - Command Prompt: .\.venv\Scripts\activate.bat
4. Install dependencies:
   pip install -r requirements.txt
5. Set up or update the database: `python -m flask --app app setup-db` (also run this after app updates that change the database).
6. Start the app on the host computer: `python app.py`. Keep this terminal open
   while the restaurant uses the app; press Ctrl+C to stop it.
7. On the host, open `http://localhost:5000`. For phones, run `ipconfig` on the
   host, find its local IPv4 address, and open `http://<host-ip>:5000` on each
   phone (for example, `http://192.168.1.20:5000`). `localhost` on a phone
   points to the phone itself. If Windows asks, allow Python on **Private**
   networks. Keep the host and phones on the same Wi-Fi/local network.

## What works now

- Menu page: view and manage menu items.
- Tables page: select a table and see whether it has an open order.
- Order page: save notes before taking food orders, add and remove items, edit
  quantities, view the saved total, and reset the table for a new order.
- Ticket preview: review the current order and select Print ticket to open the
  device's print dialog. The network printer must be available on that device.

## Notes

- The database is stored locally in the project under the db folder.
- Database changes are applied only when the explicit setup command is run.
- To back up, stop the app and copy `db/restaurant.db` to a safe location outside
  this folder. To restore, stop the app and replace `db/restaurant.db` with that
  copy before starting it again. Do not run `setup-db --reset` to restore data.
- Keep the app on the restaurant's trusted local network; do not forward port
  5000 to the internet.

For implementation details and test instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).
