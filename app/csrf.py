import hmac
import secrets

from flask import abort, request, session


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def protect_post():
    if request.method != "POST":
        return
    expected = session.get("csrf_token", "")
    received = request.form.get("csrf_token", "")
    if not expected or not hmac.compare_digest(expected, received):
        abort(400, description="Invalid form token. Refresh the page and try again.")
