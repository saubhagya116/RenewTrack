import os, sqlite3, secrets
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, abort, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "renewtrack.db")
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL,
            cycle TEXT NOT NULL, next_renewal TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active', notes TEXT DEFAULT '',
            invoice TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(subscriptions)").fetchall()}
        if "user_id" not in columns:
            con.execute("ALTER TABLE subscriptions ADD COLUMN user_id INTEGER NOT NULL DEFAULT 0")
        con.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)")
        con.commit()

def seed_user(user_id):
    with db() as con:
        count = con.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()[0]
        if count == 0:
            # Claim legacy demo rows from the pre-login version for the first account only.
            users_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if users_count == 1:
                con.execute("UPDATE subscriptions SET user_id=? WHERE user_id=0", (user_id,))
                count = con.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id=?", (user_id,)).fetchone()[0]
            if count == 0:
                samples = [
                    ("Netflix", "Entertainment", 649, "Monthly", (date.today()+timedelta(days=3)).isoformat(), "Active", "Premium plan", user_id),
                    ("Spotify", "Music", 119, "Monthly", (date.today()+timedelta(days=8)).isoformat(), "Active", "Student plan", user_id),
                    ("Google One", "Cloud Storage", 1300, "Yearly", (date.today()+timedelta(days=24)).isoformat(), "Active", "100 GB storage", user_id),
                    ("Canva Pro", "Productivity", 499, "Monthly", (date.today()+timedelta(days=15)).isoformat(), "Active", "Design tools", user_id)
                ]
                con.executemany("""INSERT INTO subscriptions
                    (name,category,amount,cycle,next_renewal,status,notes,user_id)
                    VALUES (?,?,?,?,?,?,?,?)""", samples)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        g.user = {"id": session["user_id"], "name": session.get("user_name", "Member"), "email": session.get("user_email", "")}
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_user():
    if session.get("user_id"):
        return {"current_user": {"name": session.get("user_name", "Member"), "email": session.get("user_email", "")}}
    return {"current_user": None}

def monthly_cost(row):
    amount = float(row["amount"])
    return amount if row["cycle"] == "Monthly" else amount / 12 if row["cycle"] == "Yearly" else amount * 52 / 12

def get_dashboard_data():
    with db() as con:
        rows = con.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY next_renewal", (session["user_id"],)).fetchall()
    today = date.today()
    active = [r for r in rows if r["status"] == "Active"]
    upcoming = []
    for r in active:
        try:
            days = (date.fromisoformat(r["next_renewal"]) - today).days
        except ValueError:
            days = 9999
        if 0 <= days <= 30:
            upcoming.append({"item": r, "days": days})
    monthly = sum(monthly_cost(r) for r in active)
    return rows, active, upcoming, monthly

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Please complete every field.", "error")
        elif len(name) > 70 or len(password) < 8:
            flash("Use a name under 70 characters and a password of at least 8 characters.", "error")
        elif password != confirm:
            flash("Your passwords do not match.", "error")
        else:
            try:
                with db() as con:
                    cur = con.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                      (name, email, generate_password_hash(password)))
                    user_id = cur.lastrowid
                seed_user(user_id)
                session.clear()
                session.update(user_id=user_id, user_name=name, user_email=email)
                flash("Welcome to RenewTrack! Your account is ready.", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("An account with this email already exists. Please log in.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], user_name=user["name"], user_email=user["email"])
            flash("You're signed in. Welcome back!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")

@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    rows, active, upcoming, monthly = get_dashboard_data()
    category_totals = {}
    for r in active:
        category_totals[r["category"]] = category_totals.get(r["category"], 0) + monthly_cost(r)
    category_totals = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    return render_template("dashboard.html", rows=rows, active=active, upcoming=upcoming,
                           monthly=monthly, category_totals=category_totals,
                           yearly=monthly*12, today=date.today().isoformat())

@app.route("/subscriptions")
@login_required
def subscriptions():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "All")
    sql = "SELECT * FROM subscriptions WHERE user_id=? AND name LIKE ?"
    params = [session["user_id"], f"%{q}%"]
    if status in ("Active", "Cancelled"):
        sql += " AND status=?"
        params.append(status)
    sql += " ORDER BY next_renewal"
    with db() as con:
        rows = con.execute(sql, params).fetchall()
    return render_template("subscriptions.html", rows=rows, q=q, status=status)

@app.route("/subscriptions/new", methods=["GET", "POST"])
@app.route("/subscriptions/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def subscription_form(item_id=None):
    item = None
    if item_id:
        with db() as con:
            item = con.execute("SELECT * FROM subscriptions WHERE id=? AND user_id=?",
                               (item_id, session["user_id"])).fetchone()
        if not item:
            abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        amount = request.form.get("amount", "0")
        cycle = request.form.get("cycle", "Monthly")
        renewal = request.form.get("next_renewal", "")
        status = request.form.get("status", "Active")
        notes = request.form.get("notes", "").strip()
        if not name or not category or not renewal:
            flash("Please complete all required fields.", "error")
            return render_template("form.html", item=item)
        try:
            amount = float(amount)
            if amount < 0 or cycle not in ("Monthly", "Yearly", "Weekly") or status not in ("Active", "Cancelled"):
                raise ValueError()
            date.fromisoformat(renewal)
        except ValueError:
            flash("Enter a valid amount, billing cycle, status and renewal date.", "error")
            return render_template("form.html", item=item)
        invoice = item["invoice"] if item else ""
        upload = request.files.get("invoice")
        if upload and upload.filename:
            filename = secure_filename(upload.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                flash("Invoice must be a PDF, PNG or JPG file.", "error")
                return render_template("form.html", item=item)
            safe_name = f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{filename}"
            upload.save(os.path.join(UPLOAD_DIR, safe_name))
            invoice = safe_name
        with db() as con:
            values = (name, category, amount, cycle, renewal, status, notes, invoice)
            if item_id:
                con.execute("""UPDATE subscriptions SET name=?,category=?,amount=?,cycle=?,
                    next_renewal=?,status=?,notes=?,invoice=? WHERE id=? AND user_id=?""",
                    values + (item_id, session["user_id"]))
            else:
                con.execute("""INSERT INTO subscriptions
                    (name,category,amount,cycle,next_renewal,status,notes,invoice,user_id)
                    VALUES (?,?,?,?,?,?,?,?,?)""", values + (session["user_id"],))
        flash("Subscription saved successfully.", "success")
        return redirect(url_for("subscriptions"))
    return render_template("form.html", item=item)

@app.post("/subscriptions/<int:item_id>/delete")
@login_required
def delete_subscription(item_id):
    with db() as con:
        row = con.execute("SELECT invoice FROM subscriptions WHERE id=? AND user_id=?",
                          (item_id, session["user_id"])).fetchone()
        con.execute("DELETE FROM subscriptions WHERE id=? AND user_id=?", (item_id, session["user_id"]))
    if row and row["invoice"]:
        try: os.remove(os.path.join(UPLOAD_DIR, row["invoice"]))
        except OSError: pass
    flash("Subscription deleted.", "success")
    return redirect(url_for("subscriptions"))

@app.post("/subscriptions/<int:item_id>/toggle")
@login_required
def toggle_subscription(item_id):
    with db() as con:
        con.execute("""UPDATE subscriptions SET status =
            CASE WHEN status='Active' THEN 'Cancelled' ELSE 'Active' END
            WHERE id=? AND user_id=?""", (item_id, session["user_id"]))
    flash("Subscription status updated.", "success")
    return redirect(request.referrer or url_for("subscriptions"))

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    with db() as con:
        exists = con.execute("SELECT 1 FROM subscriptions WHERE invoice=? AND user_id=?",
                             (filename, session["user_id"])).fetchone()
    if not exists:
        abort(404)
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)

@app.route("/analytics")
@login_required
def analytics():
    rows, active, upcoming, monthly = get_dashboard_data()
    categories = {}
    for r in active:
        categories[r["category"]] = categories.get(r["category"], 0) + monthly_cost(r)
    data = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    return render_template("analytics.html", data=data, monthly=monthly, yearly=monthly*12,
                           count=len(active), rows=active)

@app.route("/about")
@login_required
def about():
    return render_template("about.html")

@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum upload size is 8 MB.", "error")
    return redirect(request.referrer or url_for("subscriptions"))

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
