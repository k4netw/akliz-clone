import docker
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db
from auth_utils import authenticate_user, register_user, get_email_by_user_id
from server_utils import add_server_to_db, create_docker_container, get_user_servers, get_container_port, stream_logs, get_server_details, start_container, stop_container, restart_container, client, remove_docker_container, remove_server_from_db
from flask_socketio import SocketIO, emit


app = Flask(__name__)
app.secret_key = 'placeholder'
socketio = SocketIO(app)

init_db()


@socketio.on('start_stream')
def handle_start_stream(data):
    server_name = data['server_name']
    emit('server_log', {'log': f'Starting {server_name}...'}, broadcast=True)
    stream_logs(server_name)


@socketio.on('control_server')
def handle_control_server(data):
    server_name = data['server_name']
    action = data['action']

    if action == 'start':
        result = start_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is starting...'}, broadcast=True)
            emit('server_log', {'log': 'Server started and ready to receive commands.'}, broadcast=True)
            stream_logs(server_name)

    elif action == 'stop':
        result = stop_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is stopping...'}, broadcast=True)

    elif action == 'restart':
        result = restart_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is restarting...'}, broadcast=True)
            emit('server_log', {'log': 'Server has been restarted! Ready to receive commands.'}, broadcast=True)
            stream_logs(server_name)


def stream_logs(server_name):
    try:
        container = client.containers.get(server_name)
        for line in container.logs(stream=True, tail=10):
            emit('server_log', {'log': line.decode('utf-8').strip()}, broadcast=True)
    except Exception as e:
        emit('server_log', {'log': f'[ERROR]: {str(e)}'}, broadcast=True)


@app.route('/')
def default():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    else:
        return redirect(url_for('servers'))


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
    used_memory = 0
    total_servers = len(user_servers)
    started_count = 0

    for server in user_servers:
        try:
            container = client.containers.get(server['name'])
            if container.status == 'running':
                server['port'] = get_container_port(server['name'])
                started_servers.append(server)
                used_memory += server['memory']
            else:
                server['port'] = "N/A"
                stopped_servers.append(server)
        except docker.errors.NotFound:
            server['port'] = "N/A"
            stopped_servers.append(server)

    started_count = len(started_servers)
    free_memory = 2000 - used_memory

    return render_template(
        'servers.html',
        started_servers=started_servers,
        stopped_servers=stopped_servers,
        started_count=started_count,
        total_servers=total_servers,
        used_memory=used_memory,
        free_memory=free_memory
    )


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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        server = get_server_details(server_id)
    except ValueError as e:
        return redirect(url_for('servers', error=str(e)))

    return render_template('serverConsole.html', server=server)


@app.route('/servers/<int:server_id>/delete', methods=['POST'])
def delete_server(server_id):
    server = get_server_details(server_id)

    if server:
        remove_docker_container(server['name'])

        remove_server_from_db(server_id)

        return redirect(url_for('servers'))

    return "Server not found", 404


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
