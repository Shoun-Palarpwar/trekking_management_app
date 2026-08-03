from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from auth_utils import role_required
from db import get_db_connection

trekker_bp = Blueprint("trekker", __name__)


@trekker_bp.route("/dashboard")
@role_required("user")
def dashboard():
    conn = get_db_connection()
    available_treks = conn.execute(
        "SELECT COUNT(*) c FROM treks WHERE status = 'Open' AND available_slots > 0"
    ).fetchone()["c"]
    my_bookings = conn.execute(
        "SELECT COUNT(*) c FROM bookings WHERE user_id = ? AND status = 'Booked'",
        (g.user["id"],),
    ).fetchone()["c"]
    upcoming = conn.execute("""
        SELECT b.*, t.name AS trek_name, t.location, t.start_date, t.status AS trek_status
        FROM bookings b JOIN treks t ON t.id = b.trek_id
        WHERE b.user_id = ? AND b.status = 'Booked'
        ORDER BY t.start_date LIMIT 5
    """, (g.user["id"],)).fetchall()
    conn.close()
    return render_template(
        "trekker/dashboard.html",
        available_treks=available_treks, my_bookings=my_bookings, upcoming=upcoming,
    )


@trekker_bp.route("/treks")
@role_required("user")
def browse_treks():
    difficulty = request.args.get("difficulty", "")
    location = request.args.get("location", "").strip()

    query = """
        SELECT t.*,
            (SELECT COUNT(*) FROM bookings b WHERE b.trek_id = t.id AND b.user_id = ? AND b.status='Booked') AS already_booked
        FROM treks t
        WHERE t.status IN ('Open', 'Approved')
    """
    params = [g.user["id"]]
    if difficulty:
        query += " AND t.difficulty = ?"
        params.append(difficulty)
    if location:
        query += " AND t.location LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY t.start_date"

    conn = get_db_connection()
    treks = conn.execute(query, params).fetchall()
    conn.close()
    return render_template(
        "trekker/treks.html", treks=treks, difficulty=difficulty, location=location
    )


@trekker_bp.route("/book/<int:trek_id>", methods=["POST"])
@role_required("user")
def book_trek(trek_id):
    conn = get_db_connection()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()

    if trek is None:
        flash("Trek not found.", "danger")
    elif trek["status"] != "Open":
        flash("This trek is not currently open for booking.", "danger")
    elif trek["available_slots"] <= 0:
        flash("Sorry, this trek is fully booked.", "danger")
    else:
        existing = conn.execute(
            "SELECT id FROM bookings WHERE user_id=? AND trek_id=? AND status='Booked'",
            (g.user["id"], trek_id),
        ).fetchone()
        if existing:
            flash("You have already booked this trek.", "warning")
        else:
            conn.execute(
                "INSERT INTO bookings (user_id, trek_id, booking_date, status) VALUES (?, ?, ?, 'Booked')",
                (g.user["id"], trek_id, datetime.utcnow().isoformat()),
            )
            conn.execute(
                "UPDATE treks SET available_slots = available_slots - 1 WHERE id = ?", (trek_id,)
            )
            conn.commit()
            flash("Trek booked successfully!", "success")

    conn.close()
    return redirect(url_for("trekker.browse_treks"))


@trekker_bp.route("/bookings")
@role_required("user")
def my_bookings():
    conn = get_db_connection()
    bookings = conn.execute("""
        SELECT b.*, t.name AS trek_name, t.location, t.difficulty, t.start_date, t.end_date, t.status AS trek_status
        FROM bookings b JOIN treks t ON t.id = b.trek_id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
    """, (g.user["id"],)).fetchall()
    conn.close()
    return render_template("trekker/bookings.html", bookings=bookings)


@trekker_bp.route("/bookings/cancel/<int:booking_id>", methods=["POST"])
@role_required("user")
def cancel_booking(booking_id):
    conn = get_db_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, g.user["id"])
    ).fetchone()
    if booking is None:
        flash("Booking not found.", "danger")
    elif booking["status"] != "Booked":
        flash("This booking cannot be cancelled.", "warning")
    else:
        conn.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
        conn.execute(
            "UPDATE treks SET available_slots = available_slots + 1 WHERE id = ?",
            (booking["trek_id"],),
        )
        conn.commit()
        flash("Booking cancelled.", "info")
    conn.close()
    return redirect(url_for("trekker.my_bookings"))


@trekker_bp.route("/profile", methods=["GET", "POST"])
@role_required("user")
def profile():
    conn = get_db_connection()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        contact = request.form.get("contact", "").strip()
        new_password = request.form.get("new_password", "")

        if new_password:
            if len(new_password) < 6:
                flash("New password must be at least 6 characters.", "danger")
                conn.close()
                return render_template("trekker/profile.html", user=g.user)
            conn.execute(
                "UPDATE accounts SET name=?, email=?, contact=?, password_hash=? WHERE id=?",
                (name, email, contact, generate_password_hash(new_password), g.user["id"]),
            )
        else:
            conn.execute(
                "UPDATE accounts SET name=?, email=?, contact=? WHERE id=?",
                (name, email, contact, g.user["id"]),
            )
        conn.commit()
        conn.close()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("trekker.profile"))

    conn.close()
    return render_template("trekker/profile.html", user=g.user)
