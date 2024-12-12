import os  # for checking if the database file exists
import sqlite3  # for SQLite database operations

DB_NAME = 'aklizDB.sqlite'  # name of the database file

def init_db():
    if not os.path.exists(DB_NAME):  # check if the database file exists
        conn = sqlite3.connect(DB_NAME)  # create a new database file
        with conn:  # automatically commit or rollback changes
            conn.execute('''CREATE TABLE IF NOT EXISTS Users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique user ID
                            email VARCHAR(100) NOT NULL UNIQUE,  -- user email, must be unique
                            password VARCHAR(255) NOT NULL  -- hashed password
                        )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS Servers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique server ID
                            name VARCHAR(100) NOT NULL UNIQUE,  -- server name, must be unique
                            memory INTEGER NOT NULL,  -- memory allocated to the server
                            rcon_password VARCHAR(255) NOT NULL  -- RCON password for server management
                        )''')

            conn.execute('''CREATE TABLE IF NOT EXISTS UserServers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique link ID
                            userID INTEGER,  -- foreign key referencing Users
                            serverID INTEGER,  -- foreign key referencing Servers
                            FOREIGN KEY (userID) REFERENCES Users(id),  -- enforce relationship with Users
                            FOREIGN KEY (serverID) REFERENCES Servers(id)  -- enforce relationship with Servers
                        )''')
        conn.close()
        print("Database and tables initialized.")  # confirmation message
    else:
        print("Database already exists.")  # message if database already exists
