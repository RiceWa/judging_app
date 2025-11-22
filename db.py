import sqlite3
import streamlit as st
import hashlib

DB_NAME = "judging.db"

@st.cache_resource
def get_connection():
    # Return a cached SQLite connection
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Create tables if they do not exist
    conn = get_connection()
    cur = conn.cursor()

    # Judges table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS judges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        );
    """)

    # Competitors table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)

    # Scores table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            judge_id INTEGER NOT NULL,
            competitor_id INTEGER NOT NULL,
            value REAL NOT NULL,
            FOREIGN KEY (judge_id) REFERENCES judges(id),
            FOREIGN KEY (competitor_id) REFERENCES competitors(id)
        );
    """)

    # Users table for admin and judge logins
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'judge')),
            judge_id INTEGER,
            FOREIGN KEY (judge_id) REFERENCES judges(id)
        );
    """)

    create_default_admin_if_missing(conn)
    conn.commit()


# --- CRUD operations ---

def get_judges():
    conn = get_connection()
    return conn.execute("SELECT * FROM judges ORDER BY id").fetchall()

def get_judges_with_user():
    conn = get_connection()
    return conn.execute("""
        SELECT j.*, u.username
        FROM judges j
        LEFT JOIN users u ON u.judge_id = j.id AND u.role = 'judge'
        ORDER BY j.id
    """).fetchall()

def insert_judge(name, email):
    conn = get_connection()
    conn.execute("INSERT INTO judges (name, email) VALUES (?, ?)", (name, email))
    conn.commit()

def create_judge_account(name, email, username, password):
    """
    Create judge record and associated user account.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO judges (name, email) VALUES (?, ?)", (name, email))
        judge_id = cur.lastrowid
        cur.execute(
            "INSERT INTO users (username, password_hash, role, judge_id) VALUES (?, ?, 'judge', ?)",
            (username, hash_password(password), judge_id)
        )
    except sqlite3.IntegrityError:
        conn.rollback()
        raise
    conn.commit()
    return judge_id

def get_judge_by_id(judge_id):
    conn = get_connection()
    return conn.execute("SELECT * FROM judges WHERE id = ?", (judge_id,)).fetchone()

def update_judge_account(judge_id, name, email, username, password=None):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE judges SET name = ?, email = ? WHERE id = ?",
            (name, email, judge_id)
        )
        if password:
            cur.execute(
                "UPDATE users SET username = ?, password_hash = ? WHERE judge_id = ?",
                (username, hash_password(password), judge_id)
            )
        else:
            cur.execute(
                "UPDATE users SET username = ? WHERE judge_id = ?",
                (username, judge_id)
            )
    except sqlite3.IntegrityError:
        conn.rollback()
        raise
    conn.commit()

def delete_judge_account(judge_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scores WHERE judge_id = ?", (judge_id,))
    cur.execute("DELETE FROM users WHERE judge_id = ?", (judge_id,))
    cur.execute("DELETE FROM judges WHERE id = ?", (judge_id,))
    conn.commit()

def get_competitors():
    conn = get_connection()
    return conn.execute("SELECT * FROM competitors ORDER BY id").fetchall()

def insert_competitor(name):
    conn = get_connection()
    conn.execute(
        "INSERT INTO competitors (name) VALUES (?)",
        (name,)
    )
    conn.commit()

def update_competitor(competitor_id, name):
    conn = get_connection()
    conn.execute(
        "UPDATE competitors SET name = ? WHERE id = ?",
        (name, competitor_id)
    )
    conn.commit()

def delete_competitor(competitor_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM scores WHERE competitor_id = ?", (competitor_id,))
    cur.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
    conn.commit()


def replace_scores_for_judge(judge_id, scores_dict):
    # Replace all scores for a judge
    conn = get_connection()

    conn.execute("DELETE FROM scores WHERE judge_id = ?", (judge_id,))
    for competitor_id, value in scores_dict.items():
        conn.execute(
            "INSERT INTO scores (judge_id, competitor_id, value) VALUES (?, ?, ?)",
            (judge_id, competitor_id, value)
        )
    conn.commit()

def get_scores_for_judge(judge_id):
    """
    Return existing scores for a judge as:
      {competitor_id: value}
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT competitor_id, value FROM scores WHERE judge_id = ?",
        (judge_id,)
    )
    rows = cur.fetchall()
    return {row["competitor_id"]: row["value"] for row in rows}

def get_leaderboard():
    # Return totals and averages per competitor
    conn = get_connection()
    return conn.execute("""
        SELECT 
            c.id AS competitor_id,
            c.name AS competitor_name,
            COUNT(s.id) AS num_scores,
            COALESCE(SUM(s.value), 0) AS total_score,
            COALESCE(AVG(s.value), 0) AS avg_score
        FROM competitors c
        LEFT JOIN scores s ON c.id = s.competitor_id
        GROUP BY c.id, c.name
        ORDER BY avg_score DESC;
    """).fetchall()


# --- Auth helpers ---

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def create_default_admin_if_missing(conn):
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'")
    row = cur.fetchone()
    if row and row["cnt"] == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, judge_id) VALUES (?, ?, 'admin', NULL)",
            ("admin", hash_password("admin"))
        )

def authenticate_user(username, password):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    if row and row["password_hash"] == hash_password(password):
        return row
    return None
