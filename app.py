import os
import sqlite3
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = "sipkel-secret-key"

DB_PATH = os.path.join(os.path.dirname(__file__), "sipkel.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                nim TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                capacity INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(room_id) REFERENCES rooms(id)
            )
            """
        )

        admin_exists = conn.execute(
            "SELECT id FROM users WHERE nim = 'admin'"
        ).fetchone()
        if not admin_exists:
            conn.execute(
                "INSERT INTO users (name, nim, password, role) VALUES (?, ?, ?, ?)",
                ("Administrator", "admin", "admin123", "admin"),
            )

        room_count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        if room_count == 0:
            rooms = [
                ("Ruang 101", "Gedung A", 50),
                ("Ruang 102", "Gedung A", 40),
                ("Ruang 201", "Gedung B", 60),
                ("Ruang 202", "Gedung B", 30),
                ("Lab Komputer", "Gedung C", 25),
            ]
            conn.executemany(
                "INSERT INTO rooms (name, location, capacity) VALUES (?, ?, ?)",
                rooms,
            )

        conn.commit()


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    with get_db_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


def get_rooms():
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT * FROM rooms ORDER BY location, name"
        ).fetchall()


def has_time_conflict(room_id, date, start_time, end_time, booking_id=None):
    with get_db_connection() as conn:
        query = """
            SELECT id FROM bookings
            WHERE room_id = ? AND date = ? AND status IN ('pending', 'approved')
            AND (? < end_time AND ? > start_time)
        """
        if booking_id:
            query += " AND id != ?"
            params = (room_id, date, start_time, end_time, booking_id)
        else:
            params = (room_id, date, start_time, end_time)
        result = conn.execute(query, params).fetchone()
        return result is not None


@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nim = request.form.get("nim", "").strip()
        password = request.form.get("password", "")

        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE nim = ? AND password = ?",
                (nim, password),
            ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            flash("Login berhasil!", "success")
            return redirect(url_for("dashboard"))

        flash("NIM atau password salah.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        nim = request.form.get("nim", "").strip()
        password = request.form.get("password", "")

        if not name or not nim or not password:
            flash("Semua field wajib diisi.", "error")
            return render_template("register.html")

        with get_db_connection() as conn:
            existing_user = conn.execute(
                "SELECT id FROM users WHERE nim = ?",
                (nim,),
            ).fetchone()

            if existing_user:
                flash("NIM sudah terdaftar.", "error")
                return render_template("register.html")

            conn.execute(
                "INSERT INTO users (name, nim, password, role) VALUES (?, ?, ?, 'student')",
                (name, nim, password),
            )
            conn.commit()

        flash("Pendaftaran berhasil, silakan login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Berhasil logout.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    with get_db_connection() as conn:
        if user["role"] == "admin":
            bookings = conn.execute(
                """
                SELECT b.*, r.name AS room_name, r.location, u.name AS student_name, u.nim
                FROM bookings b
                JOIN rooms r ON r.id = b.room_id
                JOIN users u ON u.id = b.user_id
                ORDER BY b.date DESC, b.start_time DESC
                """
            ).fetchall()
        else:
            bookings = conn.execute(
                """
                SELECT b.*, r.name AS room_name, r.location
                FROM bookings b
                JOIN rooms r ON r.id = b.room_id
                WHERE b.user_id = ?
                ORDER BY b.date DESC, b.start_time DESC
                """,
                (user["id"],),
            ).fetchall()

    return render_template("dashboard.html", user=user, bookings=bookings, rooms=get_rooms())


@app.route("/book", methods=["GET", "POST"])
def book():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if request.method == "POST":
        room_id = request.form.get("room_id")
        booking_date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        purpose = request.form.get("purpose", "").strip()

        if not all([room_id, booking_date, start_time, end_time, purpose]):
            flash("Semua field harus diisi.", "error")
            return render_template("book.html", rooms=get_rooms())

        try:
            room_id = int(room_id)
        except (TypeError, ValueError):
            flash("Ruangan tidak valid.", "error")
            return render_template("book.html", rooms=get_rooms())

        if start_time >= end_time:
            flash("Jam selesai harus lebih besar dari jam mulai.", "error")
            return render_template("book.html", rooms=get_rooms())

        if has_time_conflict(room_id, booking_date, start_time, end_time):
            flash("Ruangan sudah dipinjam pada jadwal yang sama.", "error")
            return render_template("book.html", rooms=get_rooms())

        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO bookings (user_id, room_id, date, start_time, end_time, purpose, status)
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (user["id"], room_id, booking_date, start_time, end_time, purpose),
            )
            conn.commit()

        flash("Permintaan peminjaman berhasil dikirim.", "success")
        return redirect(url_for("dashboard"))

    return render_template("book.html", rooms=get_rooms())


@app.route("/booking/<int:booking_id>/status", methods=["POST"])
def update_booking_status(booking_id):
    user = get_current_user()
    if not user or user["role"] != "admin":
        flash("Anda tidak memiliki akses.", "error")
        return redirect(url_for("dashboard"))

    status = request.form.get("status")
    if status not in {"approved", "rejected", "pending"}:
        flash("Status tidak valid.", "error")
        return redirect(url_for("dashboard"))

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE bookings SET status = ? WHERE id = ?",
            (status, booking_id),
        )
        conn.commit()

    flash("Status peminjaman berhasil diperbarui.", "success")
    return redirect(url_for("dashboard"))


@app.route("/history")
def history():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    with get_db_connection() as conn:
        bookings = conn.execute(
            """
            SELECT b.*, r.name AS room_name, r.location
            FROM bookings b
            JOIN rooms r ON r.id = b.room_id
            WHERE b.user_id = ?
            ORDER BY b.date DESC, b.start_time DESC
            """,
            (user["id"],),
        ).fetchall()

    return render_template("history.html", user=user, bookings=bookings)


@app.before_request
def load_context():
    if request.endpoint in {"login", "register"}:
        return
    if session.get("user_id"):
        session["user"] = get_current_user()


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)

