# Restaurant App

A simple local-first restaurant ordering app for tracking menu items, tables, and orders.

## Requirements

- Python 3.10+
- Flask
- SQLite

## Local setup

1. Open a terminal in the project folder.
2. Create a virtual environment:
   python -m venv .venv
3. Activate it:
   - Windows PowerShell: .\.venv\Scripts\Activate.ps1
   - Command Prompt: .\.venv\Scripts\activate.bat
4. Install dependencies:
   pip install -r requirements.txt
5. Initial database setup (once):
   flask --app app setup-db
   
   or if using the app module directly:
   python -m flask --app app setup-db
6. Run the app:
   flask --app app run
   
   or:
   python app.py
7. Open the app in your browser at:
   http://localhost:5000

## What works now

- Menu page: view and manage menu items.
- Tables page: select a table and see whether it has an open order.
- Order page: add and remove items, edit quantities, and view the saved total.
  Notes, reset, and printing are still in development.

## Notes

- The database is stored locally in the project under the db folder.
- The database is only initialized when the explicit setup command is run.
- This is intentionally a lightweight MVP focused on local use and easy maintenance.

For implementation details and test instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).
