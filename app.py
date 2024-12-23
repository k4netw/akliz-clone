import docker
from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db
from auth_utils import authenticate_user, register_user, get_email_by_user_id
from server_utils import add_server_to_db, create_docker_container, get_user_servers, get_container_port, stream_logs, get_server_details, start_container, stop_container, restart_container, client, remove_docker_container, remove_server_from_db
from flask_socketio import SocketIO, emit

app = Flask(__name__)  # initialize Flask app
app.secret_key = 'placeholder'  # session encryption key
socketio = SocketIO(app)  # enable real-time Socket.IO features

init_db()  # initialize the database

# Socket.IO events
@socketio.on('start_stream')  # start streaming server logs
def handle_start_stream(data):
    server_name = data['server_name']
    emit('server_log', {'log': f'Starting {server_name}...'}, broadcast=True)  # notify all clients
    stream_logs(server_name)  # start streaming logs

@socketio.on('control_server')  # control server actions (start, stop, restart)
def handle_control_server(data):
    server_name = data['server_name']
    action = data['action']

    if action == 'start':  # start the server
        result = start_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is starting...'}, broadcast=True)
            stream_logs(server_name)

    elif action == 'stop':  # stop the server
        result = stop_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is stopping...'}, broadcast=True)

    elif action == 'restart':  # restart the server
        result = restart_container(server_name)
        if result:
            emit('server_log', {'log': f'{server_name} is restarting...'}, broadcast=True)
            stream_logs(server_name)

def stream_logs(server_name):  # continuously stream server logs
    try:
        container = client.containers.get(server_name)
        for line in container.logs(stream=True, tail=10):
            emit('server_log', {'log': line.decode('utf-8').strip()}, broadcast=True)
    except Exception as e:
        emit('server_log', {'log': f'[ERROR]: {str(e)}'}, broadcast=True)

# Flask routes
@app.route('/')  # home route
def default():
    if 'user_id' not in session:  # redirect to login if not logged in
        return redirect(url_for('login'))
    return redirect(url_for('servers'))  # redirect to servers page if logged in

@app.route('/login', methods=['GET', 'POST'])  # login route
def login():
    if request.method == 'POST':  # process login form
        email = request.form['email']
        password = request.form['password']
        user_id = authenticate_user(email, password)

        if user_id:  # successful login
            session['user_id'] = user_id
            session['email'] = get_email_by_user_id(user_id)
            flash('Login successful!', 'success')
            return redirect(url_for('servers'))
        else:
            flash('Invalid email or password. Please try again.', 'error')

    return render_template('login.html')  # show login form

@app.route('/register', methods=['GET', 'POST'])  # registration route
def register():
    if request.method == 'POST':  # process registration form
        email = request.form['email']
        confirm_email = request.form['confirm-email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        success, message = register_user(email, confirm_email, password, confirm_password)
        if not success:
            flash(message, 'error')  # show error message
            return render_template('register.html', email=email, confirm_email=confirm_email)

        flash(message, 'success')  # show success message
        return redirect(url_for('login'))

    return render_template('register.html')  # show registration form

@app.route('/servers')  # list all servers
def servers():
    if 'user_id' not in session:  # ensure user is logged in
        return redirect(url_for('login'))

    user_servers = get_user_servers(session['user_id'])  # get servers owned by user
    started_servers = []
    stopped_servers = []
    used_memory = 0

    for server in user_servers:  # categorize servers as started or stopped
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

    return render_template(
        'servers.html',
        started_servers=started_servers,
        stopped_servers=stopped_servers,
        started_count=len(started_servers),
        total_servers=len(user_servers),
        used_memory=used_memory,
        free_memory=2000 - used_memory  # calculate free memory
    )

@app.route('/servers/new', methods=['GET', 'POST'])  # create a new server
def newServer():
    if 'user_id' not in session:  # ensure user is logged in
        return redirect(url_for('login'))

    if request.method == 'POST':  # handle server creation form
        server_name = request.form.get('server_name')
        memory = request.form.get('memory')

        if not server_name:  # validate server name
            flash("Server name cannot be empty.", "error")
            return redirect(url_for('servers'))

        success, message = add_server_to_db(server_name, memory, session['user_id'])
        if not success:
            flash(message, "error")
            return redirect(url_for('servers'))

        success, message = create_docker_container(server_name, memory)
        flash(message, "success" if success else "error")  # show success or error message

        return redirect(url_for('servers'))

    return render_template('newServer.html')  # show server creation form

@app.route('/servers/<int:server_id>/console', methods=['GET'])  # manage a server console
def manage_server(server_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        server = get_server_details(server_id)
    except ValueError as e:  # handle invalid server ID
        return redirect(url_for('servers', error=str(e)))

    return render_template('serverConsole.html', server=server)  # render server console

@app.route('/servers/<int:server_id>/delete', methods=['POST'])  # delete a server
def delete_server(server_id):
    server = get_server_details(server_id)
    if server:
        remove_docker_container(server['name'])  # remove Docker container
        remove_server_from_db(server_id)  # delete server record
        return redirect(url_for('servers'))
    return "Server not found", 404  # return 404 if server doesn't exist

@app.route('/account')  # user account page
def account():
    if 'user_id' not in session:  # ensure user is logged in
        return redirect(url_for('login'))
    return render_template('account.html')  # render account page

@app.route('/logout')  # log the user out
def logout():
    session.pop('user_id', None)  # clear session
    flash('You have been logged out.', 'info')  # show logout message
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)  # start Flask app in debug mode
