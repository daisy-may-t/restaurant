import os

from flask import Flask

from .db import close_db, init_db
from .routes import register_routes


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config["DATABASE"] = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "db", "restaurant.db"
    )

    register_routes(app)

    @app.cli.command("setup-db")
    def setup_db_command():
        """Initialise the SQLite database and tables."""
        init_db()
        print("Database initialized.")

    app.teardown_appcontext(close_db)

    return app
