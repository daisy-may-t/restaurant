# Development

Follow [README.md](README.md) to set up the project and activate the virtual environment.

## Menu CRUD

The menu uses GET to display pages and POST forms to add, edit, and delete items.
No JavaScript or HTTP method overrides are needed. Prices must be non-negative
and have at most two decimal places, with a maximum of 999.99 pounds. Prices are
stored as integer pence. POST forms carry a CSRF token.

## Tests

Run from the project folder with the virtual environment activated:

```text
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases, separate from the application database.

## Resetting a test database

`flask --app app setup-db --reset` discards all menu, table, and order data and
creates the current schema. Use it only after backing up data you want to keep.
Ordinary `setup-db` is safe to rerun and rejects an old incompatible schema.
