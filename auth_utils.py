import sqlite3  # for database connection
import bcrypt  # for password hashing
import re  # for email validation

DATABASE_PATH = 'aklizDB.sqlite'  # path to the SQLite database

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)  # connect to database
    conn.row_factory = sqlite3.Row  # return rows as dictionaries
    return conn

def register_user(email, confirm_email, password, confirm_password):
    if email != confirm_email:  # check if emails match
        return False, "Email addresses do not match."

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):  # validate email format
        return False, "Invalid email format."

    if len(password) < 8:  # ensure password length
        return False, "Password must be at least 8 characters long."

    if password != confirm_password:  # check if passwords match
        return False, "Passwords do not match."

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())  # hash the password
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO Users (email, password) VALUES (?, ?)", (email, hashed_password))  # insert user
        conn.commit()
    except sqlite3.IntegrityError:  # handle duplicate email
        return False, "Email is already registered."
    finally:
        conn.close()

    return True, "Registration successful!"  # return success message

def authenticate_user(email, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM Users WHERE email = ?", (email,)).fetchone()  # fetch user by email
    conn.close()
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):  # verify password
        return user['id']  # return user ID on success
    return None  # return None if authentication fails

def get_email_by_user_id(user_id):
    conn = get_db_connection()
    result = conn.execute('SELECT email FROM Users WHERE id = ?', (user_id,)).fetchone()  # fetch email by user ID
    conn.close()
    return result['email'] if result else None  # return email or None
