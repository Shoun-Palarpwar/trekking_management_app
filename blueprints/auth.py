from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        role = request.form.get("role")  # 'staff' or 'user' only - no admin self-registration
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        contact = request.form.get("contact", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if role not in ("staff", "user"):
            error = "Invalid role selected."
        elif not (name and username and email and password):
            error = "All required fields must be filled."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        conn = get_db_connection()
        if error is None:
            existing = conn.execute(
                "SELECT id FROM accounts WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if existing:
                error = "Username or email already registered."

        if error:
            conn.close()
            flash(error, "danger")
            return render_template("auth/register.html")

        # Staff need admin approval before they can access the dashboard.
        initial_status = "pending" if role == "staff" else "active"

        conn.execute(
            """INSERT INTO accounts (username, email, password_hash, role, name, contact, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username, email, generate_password_hash(password), role,
                name, contact, initial_status, datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        if role == "staff":
            flash("Registration successful! Your account is pending admin approval before you can log in to the dashboard.", "success")
        else:
            flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        account = conn.execute(
            "SELECT * FROM accounts WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if account is None or not check_password_hash(account["password_hash"], password):
            flash("Incorrect username or password.", "danger")
            return render_template("auth/login.html")

        if account["status"] == "blacklisted":
            flash("Your account has been blacklisted. Contact the admin for assistance.", "danger")
            return render_template("auth/login.html")

        session.clear()
        session["user_id"] = account["id"]
        flash(f"Welcome back, {account['name']}!", "success")

        if account["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        elif account["role"] == "staff":
            return redirect(url_for("staff.dashboard"))
        else:
            return redirect(url_for("trekker.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))
