import sqlite3
import bcrypt

DATABASE_PATH = 'aklizDB.sqlite'

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def register_user(email, password):
    conn = get_db_connection()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        conn.execute("INSERT INTO Users (email, password) VALUES (?, ?)", (email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
    return True

def authenticate_user(email, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return user['id']
    return None
