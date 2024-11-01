from flask import Flask, render_template
from database import init_db, get_db_connection

app = Flask(__name__)

init_db()

@app.route('/')
def home():
    return render_template('mainLayout.html')

@app.route('/login')
def login():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
