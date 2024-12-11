import docker
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db
from auth_utils import authenticate_user, register_user, get_email_by_user_id
from server_utils import add_server_to_db, create_docker_container, get_user_servers, get_container_port

app = Flask(__name__)
app.secret_key = 'placeholder'

init_db()

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_id = authenticate_user(email, password)

        if user_id:
            session['user_id'] = user_id
            email = get_email_by_user_id(user_id)
            session['email'] = email
            flash('Login successful!', 'success')
            return redirect(url_for('servers'))
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
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_servers = get_user_servers(user_id)

    client = docker.from_env()
    started_servers = []
    stopped_servers = []

    for server in user_servers:
        try:
            container = client.containers.get(server['name'])
            if container.status == 'running':
                server['port'] = get_container_port(server['name'])
                started_servers.append(server)
            else:
                server['port'] = "N/A"
                stopped_servers.append(server)
        except docker.errors.NotFound:
            server['port'] = "N/A"
            stopped_servers.append(server)

    return render_template('servers.html', started_servers=started_servers, stopped_servers=stopped_servers)


@app.route('/servers/new', methods=['GET', 'POST'])
def newServer():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('newServer.html')

    if request.method == 'POST':
        server_name = request.form.get('server_name')
        memory = request.form.get('memory')

        if not server_name:
            flash("Server name cannot be empty.", "error")
            return redirect(url_for('servers'))

        success, message = add_server_to_db(server_name, memory, session['user_id'])
        if not success:
            flash(message, "error")
            return redirect(url_for('servers'))

        success, message = create_docker_container(server_name, memory)
        if not success:
            flash(message, "error")
        else:
            flash(message, "success")

        return redirect(url_for('servers'))


@app.route('/servers/<int:server_id>/console', methods=['GET'])
def manage_server(server_id):
    return f"Managing server with ID: {server_id}"

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('account.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
