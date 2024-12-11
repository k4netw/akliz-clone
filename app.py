from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db
from auth_utils import authenticate_user, register_user

app = Flask(__name__)
app.secret_key = 'placeholder'

init_db()

@app.route('/')
def home():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('mainLayout.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_id = authenticate_user(email, password)

        if user_id:
            session['user_id'] = user_id
            flash('Login successful!', 'success')
            return redirect(url_for('servers'))  # Replace 'dashboard' with your target route
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        confirm_email = request.form['confirm-email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        success, message = register_user(email, confirm_email, password, confirm_password)
        if not success:
            flash(message, 'error')
            return render_template('register.html', email=email, confirm_email=confirm_email, password=password, confirm_password=confirm_password)


        flash(message, 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/servers')
def servers():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))
    return render_template('mainLayout.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
