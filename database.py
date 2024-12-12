import os
import sqlite3

DB_NAME = 'aklizDB.sqlite'

def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS Users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email VARCHAR(100) NOT NULL UNIQUE,
                            password VARCHAR(255) NOT NULL
                        )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS Servers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            name VARCHAR(100) NOT NULL UNIQUE,
                            memory INTEGER NOT NULL,
                            rcon_password VARCHAR(255) NOT NULL
                        )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS UserServers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            userID INTEGER,
                            serverID INTEGER,
                            FOREIGN KEY (userID) REFERENCES Users(id),
                            FOREIGN KEY (serverID) REFERENCES Servers(id)
                        )''')
        conn.close()
        print("Database and tables initialized.")
    else:
        print("Database already exists.")