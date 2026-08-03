from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from auth_utils import role_required
from db import get_db_connection

staff_bp = Blueprint("staff", __name__)


def _pending_or_blacklisted_response():
    """If staff isn't approved yet, show a holding page instead of the dashboard."""
    if g.user["status"] == "pending":
        return render_template("staff/pending.html")
    if g.user["status"] == "blacklisted":
        flash("Your staff account has been blacklisted. Contact the admin.", "danger")
        return redirect(url_for("auth.logout"))
    return None


@staff_bp.route("/dashboard")
@role_required("staff")
def dashboard():
    blocked = _pending_or_blacklisted_response()
    if blocked:
        return blocked

    conn = get_db_connection()
    assigned_treks = conn.execute("""
        SELECT t.*,
            (SELECT COUNT(*) FROM bookings b WHERE b.trek_id = t.id AND b.status = 'Booked') AS registered_count
        FROM treks t
        WHERE t.assigned_staff_id = ?
        ORDER BY t.start_date
    """, (g.user["id"],)).fetchall()
    conn.close()
    return render_template("staff/dashboard.html", treks=assigned_treks)


@staff_bp.route("/trek/<int:trek_id>", methods=["GET", "POST"])
@role_required("staff")
def manage_trek(trek_id):
    blocked = _pending_or_blacklisted_response()
    if blocked:
        return blocked

    conn = get_db_connection()
    trek = conn.execute(
        "SELECT * FROM treks WHERE id = ? AND assigned_staff_id = ?",
        (trek_id, g.user["id"]),
    ).fetchone()
    if trek is None:
        conn.close()
        flash("Trek not found or not assigned to you.", "danger")
        return redirect(url_for("staff.dashboard"))

    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_slots":
            available_slots = request.form.get("available_slots", type=int)
            available_slots = max(0, min(available_slots, trek["total_slots"]))
            conn.execute("UPDATE treks SET available_slots = ? WHERE id = ?", (available_slots, trek_id))
            conn.commit()
            flash("Available slots updated.", "success")
        elif action == "set_status":
            new_status = request.form.get("status")
            if new_status in ("Open", "Closed", "Completed"):
                conn.execute("UPDATE treks SET status = ? WHERE id = ?", (new_status, trek_id))
                conn.commit()
                if new_status == "Completed":
                    conn.execute(
                        "UPDATE bookings SET status='Completed' WHERE trek_id=? AND status='Booked'",
                        (trek_id,),
                    )
                    conn.commit()
                flash(f"Trek status set to {new_status}.", "success")
        conn.close()
        return redirect(url_for("staff.manage_trek", trek_id=trek_id))

    participants = conn.execute("""
        SELECT b.*, a.name, a.email, a.contact
        FROM bookings b
        JOIN accounts a ON a.id = b.user_id
        WHERE b.trek_id = ?
        ORDER BY b.id
    """, (trek_id,)).fetchall()
    conn.close()
    return render_template("staff/trek_manage.html", trek=trek, participants=participants)
