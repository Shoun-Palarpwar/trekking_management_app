from flask import Flask, render_template, g, redirect, url_for
from db import init_db
from auth_utils import load_logged_in_user
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.staff import staff_bp
from blueprints.trekker import trekker_bp

app = Flask(__name__)
app.secret_key = "trekking-app-dev-secret-key-change-in-production"

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(staff_bp, url_prefix="/staff")
app.register_blueprint(trekker_bp, url_prefix="/trekker")

app.before_request(load_logged_in_user)


@app.route("/")
def index():
    if g.user:
        if g.user["role"] == "admin":
            return redirect(url_for("admin.dashboard"))
        elif g.user["role"] == "staff":
            return redirect(url_for("staff.dashboard"))
        else:
            return redirect(url_for("trekker.dashboard"))
    return render_template("index.html")


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
