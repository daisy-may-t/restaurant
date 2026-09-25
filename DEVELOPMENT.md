# Development

Follow [README.md](README.md) to set up the project and activate the virtual environment.

## Menu CRUD

The menu uses GET to display pages and POST forms to add, edit, and delete items.
No JavaScript or HTTP method overrides are needed. Prices must be non-negative
and have at most two decimal places.

## Tests

Run from the project folder with the virtual environment activated:

```text
python -m unittest discover -s tests -v
```

Tests use temporary SQLite databases, separate from the application database.
