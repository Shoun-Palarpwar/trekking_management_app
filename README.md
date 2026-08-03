# Trekking Management Application

A Flask + Jinja2 + Bootstrap + SQLite web application for managing treks, trek staff, and trekkers.

## Tech Stack
- **Backend:** Flask (Python), plain `sqlite3` module (no ORM, no other DB)
- **Frontend:** Jinja2 templates, HTML, CSS, Bootstrap 5 (via CDN)
- **Auth:** Custom session-based authentication (Flask `session` + Werkzeug password hashing) — no JavaScript is used for any core requirement
- **Database:** SQLite, created **programmatically** on first run (`db.py` → `init_db()`). Do not create/edit `trekking.db` manually.

## Setup & Run

```bash
# 1. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (creates trekking.db and seeds the admin account automatically)
python app.py
```

The app runs at **http://127.0.0.1:5000**

## Default Admin Login
The admin account is pre-seeded on first run (no admin self-registration, per spec):
- **Username:** `admin`
- **Password:** `admin123`

## Roles & Flow

### Admin
- Pre-existing superuser (seeded automatically).
- Create / edit / delete treks (`/admin/treks`)
- Approve, reject, or blacklist trek staff registrations (`/admin/staff`)
- Assign approved staff to a trek (`/admin/treks/assign/<id>`)
- View / blacklist / reinstate users (`/admin/users`)
- View all bookings (`/admin/bookings`)
- Search treks, staff, or users by name/ID (`/admin/search`)
- Dashboard shows totals for treks, users, staff, bookings, and pending staff approvals

### Trek Staff
- Self-register at `/register` (role: Trek Staff) → account starts as `pending`
- Cannot access the dashboard until an admin approves the account
- Once approved: view treks assigned by admin, update available slots, mark trek status (Open / Closed / Completed), and view the list of registered participants per trek

### User (Trekker)
- Self-register at `/register` (role: User)
- View treks in `Approved`/`Open` status, filter by difficulty and location
- Book a trek (blocked if not `Open`, no slots left, or already booked — prevents overbooking)
- View booking status and full trekking history, cancel active bookings
- Edit profile (name, email, contact, password)

## Business Rules Enforced
- A trek can only be booked while its status is `Open` and it has `available_slots > 0`.
- Booking decrements `available_slots`; cancelling restores it.
- Only the staff member assigned to a trek can manage it.
- Blacklisted staff/users are blocked from logging in.
- Staff accounts are blocked from the dashboard until approved by admin.

## Project Structure
```
trekking_app/
├── app.py                 # App entry point, blueprint registration
├── db.py                  # SQLite connection + programmatic schema + admin seeding
├── auth_utils.py          # Session-based login/role decorators
├── requirements.txt
├── blueprints/
│   ├── auth.py            # register / login / logout
│   ├── admin.py           # admin routes
│   ├── staff.py           # trek staff routes
│   └── trekker.py         # user (trekker) routes
├── templates/
│   ├── base.html, index.html, 404.html
│   ├── auth/               (login, register)
│   ├── admin/               (dashboard, treks, staff, users, bookings, search)
│   ├── staff/               (dashboard, trek_manage, pending)
│   └── trekker/             (dashboard, treks, bookings, profile)
└── static/css/style.css
```

## Notes
- Delete `trekking.db` and restart the app for a completely fresh database.
- No JavaScript is required for any core feature — all forms use standard HTML POST requests.
