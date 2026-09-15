from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from ml_model import predict_category, train_model

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB = os.path.join(os.path.dirname(__file__), "finance.db")

CATEGORIES = ["Food","Transport","Shopping","Bills","Entertainment","Health","Education","Other"]

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('income','expense')),
        category TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS budgets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        month TEXT NOT NULL,
        category TEXT NOT NULL,
        limit_amount REAL NOT NULL,
        UNIQUE(user_id, month, category),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()
    train_model()

@app.context_processor
def inject():
    return {"categories": CATEGORIES}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name, email, password = request.form["name"].strip(), request.form["email"].strip().lower(), request.form["password"]
        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")
        conn = db()
        try:
            conn.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                         (name,email,generate_password_hash(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("register.html", error="Email already registered.")
        conn.close()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"], session["name"] = user["id"], user["name"]
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

def current_user():
    return session.get("user_id")

@app.route("/dashboard")
def dashboard():
    uid = current_user()
    if not uid: return redirect(url_for("login"))
    conn = db()
    tx = conn.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC, id DESC", (uid,)).fetchall()
    income = conn.execute("SELECT COALESCE(SUM(amount),0) n FROM transactions WHERE user_id=? AND type='income'",(uid,)).fetchone()["n"]
    expense = conn.execute("SELECT COALESCE(SUM(amount),0) n FROM transactions WHERE user_id=? AND type='expense'",(uid,)).fetchone()["n"]
    cats = conn.execute("""SELECT category, SUM(amount) total FROM transactions
                           WHERE user_id=? AND type='expense' GROUP BY category ORDER BY total DESC""",(uid,)).fetchall()
    budgets = conn.execute("SELECT * FROM budgets WHERE user_id=? ORDER BY month DESC, category",(uid,)).fetchall()
    conn.close()
    return render_template("dashboard.html", transactions=tx, income=income, expense=expense,
                           balance=income-expense, cats=cats, budgets=budgets)

@app.route("/transactions/add", methods=["POST"])
def add_transaction():
    uid = current_user()
    if not uid: return redirect(url_for("login"))
    date = request.form["date"]
    description = request.form["description"].strip()
    amount = float(request.form["amount"])
    typ = request.form["type"]
    category = request.form.get("category","").strip()
    if typ == "expense" and (not category or category == "Auto"):
        category = predict_category(description)
    elif typ == "income":
        category = "Income"
    conn = db()
    conn.execute("""INSERT INTO transactions(user_id,date,description,amount,type,category)
                    VALUES(?,?,?,?,?,?)""",(uid,date,description,amount,typ,category))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard"))

@app.route("/transactions/delete/<int:tid>", methods=["POST"])
def delete_transaction(tid):
    uid = current_user()
    if not uid: return redirect(url_for("login"))
    conn = db()
    conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?",(tid,uid))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard"))

@app.route("/budgets/add", methods=["POST"])
def add_budget():
    uid=current_user()
    if not uid: return redirect(url_for("login"))
    month=request.form["month"]; category=request.form["category"]; limit=float(request.form["limit"])
    conn=db()
    conn.execute("""INSERT INTO budgets(user_id,month,category,limit_amount) VALUES(?,?,?,?)
                    ON CONFLICT(user_id,month,category) DO UPDATE SET limit_amount=excluded.limit_amount""",
                 (uid,month,category,limit))
    conn.commit(); conn.close()
    return redirect(url_for("dashboard"))

@app.route("/api/predict", methods=["POST"])
def api_predict():
    if not current_user(): return jsonify({"error":"Login required"}),401
    data=request.get_json(silent=True) or {}
    description=data.get("description","")
    return jsonify({"category":predict_category(description)})

@app.route("/api/insights")
def insights():
    uid=current_user()
    if not uid: return jsonify({"error":"Login required"}),401
    conn=db()
    rows=conn.execute("""SELECT category,SUM(amount) total FROM transactions
                         WHERE user_id=? AND type='expense' GROUP BY category ORDER BY total DESC""",(uid,)).fetchall()
    budget_rows=conn.execute("SELECT category,limit_amount FROM budgets WHERE user_id=? AND month=strftime('%Y-%m','now')",(uid,)).fetchall()
    conn.close()
    out=[]
    if rows:
        top=rows[0]
        out.append(f"Your highest spending category is {top['category']} (₹{top['total']:.2f}).")
    for b in budget_rows:
        spent=next((r["total"] for r in rows if r["category"]==b["category"]),0)
        if spent >= b["limit_amount"]:
            out.append(f"{b['category']} budget exceeded: ₹{spent:.2f} spent against ₹{b['limit_amount']:.2f}.")
        elif spent >= .8*b["limit_amount"]:
            out.append(f"{b['category']} spending is above 80% of its monthly budget.")
    if not out:
        out.append("Add more transactions and budgets to receive useful insights.")
    return jsonify({"insights":out})

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
