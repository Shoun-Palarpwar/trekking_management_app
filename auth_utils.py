"""
Session-based authentication helpers.
No Flask-Login is used (kept dependency-free per environment constraints);
role is stored in the Flask session and re-validated against the DB on each request.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, g
from db import get_db_connection


def load_logged_in_user():
    """Runs before every request (registered in app.py) to populate g.user."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return
    conn = get_db_connection()
    g.user = conn.execute(
        "SELECT * FROM accounts WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if g.user is None:
        session.clear()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped_view


def role_required(*roles):
    """Restrict a view to one or more roles, e.g. @role_required('admin')."""
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if g.user is None:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))
            if g.user["role"] not in roles:
                flash("You do not have permission to access that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped_view
    return decorator
