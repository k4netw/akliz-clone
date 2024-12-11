import sqlite3
import bcrypt
import re

DATABASE_PATH = 'aklizDB.sqlite'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(email, confirm_email, password, confirm_password):
    if email != confirm_email:
        return False, "Email addresses do not match."

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):  # Simple email regex
        return False, "Invalid email format."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if password != confirm_password:
        return False, "Passwords do not match."

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO Users (email, password) VALUES (?, ?)", (email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        return False, "Email is already registered."
    finally:
        conn.close()

    return True, "Registration successful!"

def authenticate_user(email, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return user['id']
    return None
