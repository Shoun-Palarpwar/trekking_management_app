from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from auth_utils import role_required
from db import get_db_connection

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    conn = get_db_connection()
    total_treks = conn.execute("SELECT COUNT(*) c FROM treks").fetchone()["c"]
    total_users = conn.execute("SELECT COUNT(*) c FROM accounts WHERE role='user'").fetchone()["c"]
    total_staff = conn.execute("SELECT COUNT(*) c FROM accounts WHERE role='staff'").fetchone()["c"]
    total_bookings = conn.execute("SELECT COUNT(*) c FROM bookings").fetchone()["c"]
    pending_staff = conn.execute(
        "SELECT COUNT(*) c FROM accounts WHERE role='staff' AND status='pending'"
    ).fetchone()["c"]
    recent_bookings = conn.execute("""
        SELECT b.*, a.name AS user_name, t.name AS trek_name
        FROM bookings b
        JOIN accounts a ON a.id = b.user_id
        JOIN treks t ON t.id = b.trek_id
        ORDER BY b.id DESC LIMIT 5
    """).fetchall()
    conn.close()
    return render_template(
        "admin/dashboard.html",
        total_treks=total_treks, total_users=total_users, total_staff=total_staff,
        total_bookings=total_bookings, pending_staff=pending_staff,
        recent_bookings=recent_bookings,
    )


# ---------------------------------------------------------------- TREKS ----
@admin_bp.route("/treks")
@role_required("admin")
def treks():
    conn = get_db_connection()
    all_treks = conn.execute("""
        SELECT t.*, a.name AS staff_name
        FROM treks t
        LEFT JOIN accounts a ON a.id = t.assigned_staff_id
        ORDER BY t.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin/treks.html", treks=all_treks)


@admin_bp.route("/treks/add", methods=["GET", "POST"])
@role_required("admin")
def add_trek():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        difficulty = request.form.get("difficulty")
        duration = request.form.get("duration", type=int)
        total_slots = request.form.get("total_slots", type=int)
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if not all([name, location, difficulty, duration, total_slots, start_date, end_date]):
            flash("All fields are required.", "danger")
            return render_template("admin/trek_form.html", trek=None)

        conn = get_db_connection()
        conn.execute(
            """INSERT INTO treks
               (name, location, difficulty, duration, total_slots, available_slots,
                status, start_date, end_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?, ?)""",
            (name, location, difficulty, duration, total_slots, total_slots,
             start_date, end_date, datetime.utcnow().isoformat()),
        )
        conn.commit()
        conn.close()
        flash("Trek created successfully.", "success")
        return redirect(url_for("admin.treks"))

    return render_template("admin/trek_form.html", trek=None)


@admin_bp.route("/treks/edit/<int:trek_id>", methods=["GET", "POST"])
@role_required("admin")
def edit_trek(trek_id):
    conn = get_db_connection()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()
    if trek is None:
        conn.close()
        flash("Trek not found.", "danger")
        return redirect(url_for("admin.treks"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        location = request.form.get("location", "").strip()
        difficulty = request.form.get("difficulty")
        duration = request.form.get("duration", type=int)
        total_slots = request.form.get("total_slots", type=int)
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("status")

        # Keep available_slots consistent if total_slots changed
        booked_count = conn.execute(
            "SELECT COUNT(*) c FROM bookings WHERE trek_id = ? AND status = 'Booked'", (trek_id,)
        ).fetchone()["c"]
        new_available = max(total_slots - booked_count, 0)

        conn.execute(
            """UPDATE treks SET name=?, location=?, difficulty=?, duration=?, total_slots=?,
               available_slots=?, start_date=?, end_date=?, status=? WHERE id=?""",
            (name, location, difficulty, duration, total_slots, new_available,
             start_date, end_date, status, trek_id),
        )
        conn.commit()
        conn.close()
        flash("Trek updated successfully.", "success")
        return redirect(url_for("admin.treks"))

    conn.close()
    return render_template("admin/trek_form.html", trek=trek)


@admin_bp.route("/treks/delete/<int:trek_id>", methods=["POST"])
@role_required("admin")
def delete_trek(trek_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM bookings WHERE trek_id = ?", (trek_id,))
    conn.execute("DELETE FROM treks WHERE id = ?", (trek_id,))
    conn.commit()
    conn.close()
    flash("Trek deleted.", "info")
    return redirect(url_for("admin.treks"))


@admin_bp.route("/treks/assign/<int:trek_id>", methods=["GET", "POST"])
@role_required("admin")
def assign_staff(trek_id):
    conn = get_db_connection()
    trek = conn.execute("SELECT * FROM treks WHERE id = ?", (trek_id,)).fetchone()
    if trek is None:
        conn.close()
        flash("Trek not found.", "danger")
        return redirect(url_for("admin.treks"))

    if request.method == "POST":
        staff_id = request.form.get("staff_id", type=int)
        new_status = "Approved" if trek["status"] == "Pending" else trek["status"]
        conn.execute(
            "UPDATE treks SET assigned_staff_id = ?, status = ? WHERE id = ?",
            (staff_id, new_status, trek_id),
        )
        conn.commit()
        conn.close()
        flash("Staff assigned to trek.", "success")
        return redirect(url_for("admin.treks"))

    approved_staff = conn.execute(
        "SELECT * FROM accounts WHERE role='staff' AND status='approved' ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("admin/assign_staff.html", trek=trek, staff_list=approved_staff)


# ---------------------------------------------------------------- STAFF ----
@admin_bp.route("/staff")
@role_required("admin")
def staff_list():
    conn = get_db_connection()
    staff = conn.execute(
        "SELECT * FROM accounts WHERE role='staff' ORDER BY status, name"
    ).fetchall()
    conn.close()
    return render_template("admin/staff.html", staff=staff)


@admin_bp.route("/staff/approve/<int:staff_id>", methods=["POST"])
@role_required("admin")
def approve_staff(staff_id):
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET status='approved' WHERE id=? AND role='staff'", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff member approved.", "success")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/staff/blacklist/<int:staff_id>", methods=["POST"])
@role_required("admin")
def blacklist_staff(staff_id):
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET status='blacklisted' WHERE id=? AND role='staff'", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff member blacklisted.", "warning")
    return redirect(url_for("admin.staff_list"))


@admin_bp.route("/staff/reinstate/<int:staff_id>", methods=["POST"])
@role_required("admin")
def reinstate_staff(staff_id):
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET status='approved' WHERE id=? AND role='staff'", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff member reinstated.", "success")
    return redirect(url_for("admin.staff_list"))


# ---------------------------------------------------------------- USERS ----
@admin_bp.route("/users")
@role_required("admin")
def users_list():
    conn = get_db_connection()
    users = conn.execute(
        "SELECT * FROM accounts WHERE role='user' ORDER BY name"
    ).fetchall()
    conn.close()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/blacklist/<int:user_id>", methods=["POST"])
@role_required("admin")
def blacklist_user(user_id):
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET status='blacklisted' WHERE id=? AND role='user'", (user_id,))
    conn.commit()
    conn.close()
    flash("User blacklisted.", "warning")
    return redirect(url_for("admin.users_list"))


@admin_bp.route("/users/reinstate/<int:user_id>", methods=["POST"])
@role_required("admin")
def reinstate_user(user_id):
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET status='active' WHERE id=? AND role='user'", (user_id,))
    conn.commit()
    conn.close()
    flash("User reinstated.", "success")
    return redirect(url_for("admin.users_list"))


# ------------------------------------------------------------- BOOKINGS ----
@admin_bp.route("/bookings")
@role_required("admin")
def bookings():
    conn = get_db_connection()
    all_bookings = conn.execute("""
        SELECT b.*, a.name AS user_name, a.username AS user_username, t.name AS trek_name
        FROM bookings b
        JOIN accounts a ON a.id = b.user_id
        JOIN treks t ON t.id = b.trek_id
        ORDER BY b.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin/bookings.html", bookings=all_bookings)


# --------------------------------------------------------------- SEARCH ----
@admin_bp.route("/search")
@role_required("admin")
def search():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "treks")
    results = []
    conn = get_db_connection()
    like = f"%{query}%"

    if query:
        if category == "treks":
            results = conn.execute(
                "SELECT * FROM treks WHERE name LIKE ? OR location LIKE ? OR CAST(id AS TEXT) = ?",
                (like, like, query),
            ).fetchall()
        elif category == "staff":
            results = conn.execute(
                "SELECT * FROM accounts WHERE role='staff' AND (name LIKE ? OR username LIKE ? OR CAST(id AS TEXT) = ?)",
                (like, like, query),
            ).fetchall()
        elif category == "users":
            results = conn.execute(
                "SELECT * FROM accounts WHERE role='user' AND (name LIKE ? OR username LIKE ? OR CAST(id AS TEXT) = ?)",
                (like, like, query),
            ).fetchall()
    conn.close()
    return render_template("admin/search.html", results=results, query=query, category=category)
