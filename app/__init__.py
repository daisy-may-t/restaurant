import os
import secrets

import click
from flask import Flask

from .csrf import csrf_token, protect_post
from .db import DEFAULT_DB_PATH, close_db, init_db
from .routes import register_routes


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config["DATABASE"] = DEFAULT_DB_PATH

    # Keep browser form tokens valid across app restarts.
    os.makedirs(app.instance_path, exist_ok=True)
    key_path = os.path.join(app.instance_path, "secret_key")
    try:
        with open(key_path, "x", encoding="ascii") as key_file:
            key_file.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    with open(key_path, encoding="ascii") as key_file:
        app.secret_key = key_file.read().strip()

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.before_request(protect_post)
    register_routes(app)

    @app.cli.command("setup-db")
    @click.option("--reset", is_flag=True, help="Discard all existing app data first.")
    def setup_db_command(reset):
        """Initialise the SQLite database and tables."""
        init_db(reset=reset)
        click.echo("Database initialized.")

    app.teardown_appcontext(close_db)
    return app
