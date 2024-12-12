import sqlite3
import string
import docker
from auth_utils import get_db_connection
from flask_socketio import emit
import random

DATABASE_PATH = 'aklizDB.sqlite'

client = docker.from_env()

rcon_connections = {}

def generate_rcon_password(length=16):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def add_server_to_db(server_name, memory, user_id):
    conn = get_db_connection()
    try:
        existing_server = conn.execute('SELECT * FROM Servers WHERE name = ?', (server_name,)).fetchone()
        if existing_server:
            return False, "Server name already exists."

        rcon_password = generate_rcon_password()

        conn.execute(
            'INSERT INTO Servers (name, memory, rcon_password) VALUES (?, ?, ?)',
            (server_name, memory, rcon_password)
        )
        server_id = conn.execute('SELECT id FROM Servers WHERE name = ?', (server_name,)).fetchone()['id']

        conn.execute('INSERT INTO UserServers (userID, serverID) VALUES (?, ?)', (user_id, server_id))
        conn.commit()
        return True, "Server added successfully."
    except sqlite3.Error as e:
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def create_docker_container(server_name, memory):
    try:
        client = docker.from_env()

        container = client.containers.run(
            image="itzg/minecraft-server",
            name=server_name,
            detach=True,
            environment={
                "EULA": "TRUE",
                "MEMORY": f"{memory}M"
            },
            ports={
                '25565/tcp': None
            }
        )
        return True, f"Docker container '{server_name}' created successfully."
    except docker.errors.DockerException as e:
        return False, f"Docker error: {str(e)}"

def get_user_servers(user_id):
    conn = get_db_connection()
    try:
        query = '''
            SELECT Servers.id, Servers.name, Servers.memory
            FROM Servers
            INNER JOIN UserServers ON Servers.id = UserServers.serverID
            WHERE UserServers.userID = ?
        '''
        servers = conn.execute(query, (user_id,)).fetchall()
        return [dict(server) for server in servers]
    finally:
        conn.close()

def get_container_port(server_name):
    try:
        container = client.containers.get(server_name)
        ports = container.attrs['NetworkSettings']['Ports']
        if ports and '25565/tcp' in ports and ports['25565/tcp']:
            return ports['25565/tcp'][0]['HostPort']
        else:
            return "Unknown"
    except docker.errors.NotFound:
        return "Not Found"
    except Exception as e:
        return f"Error: {str(e)}"

def get_server_details(server_id):
    conn = get_db_connection()
    try:
        query = '''
            SELECT Servers.id, Servers.name, Servers.memory
            FROM Servers
            WHERE Servers.id = ?
        '''
        server = conn.execute(query, (server_id,)).fetchone()
        if not server:
            raise ValueError(f"Server with ID {server_id} not found.")

        server = dict(server)
        server['port'] = get_container_port(server['name'])
        server['version'] = "1.21.4"
        server['region'] = "Europe"
        return server
    finally:
        conn.close()

def stream_logs(server_name):
    try:
        container = client.containers.get(server_name)
        for line in container.logs(stream=True, tail=10):
            emit('server_log', {'log': line.decode('utf-8').strip()})
    except Exception as e:
        emit('server_log', {'log': f'[ERROR]: {str(e)}'})

def start_container(server_name):
    client = docker.from_env()
    try:
        container = client.containers.get(server_name)
        container.start()
        return True
    except docker.errors.NotFound:
        return False

def stop_container(server_name):
    client = docker.from_env()
    try:
        container = client.containers.get(server_name)
        container.stop()
        return True
    except docker.errors.NotFound:
        return False

def restart_container(server_name):
    client = docker.from_env()
    try:
        container = client.containers.get(server_name)
        container.restart()
        return True
    except docker.errors.NotFound:
        return False


def remove_docker_container(container_name):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        print(f"Successfully removed container: {container_name}")
    except docker.errors.NotFound:
        print(f"Container {container_name} not found!")
    except Exception as e:
        print(f"Error while removing container {container_name}: {str(e)}")


def remove_server_from_db(server_id):
    conn = sqlite3.connect('aklizDB.sqlite')
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM UserServers WHERE serverID=?", (server_id,))

        cursor.execute("DELETE FROM Servers WHERE id=?", (server_id,))

        conn.commit()
        print(f"Server with ID {server_id} deleted from both UserServers and Servers.")
    except sqlite3.Error as e:
        print(f"Error while deleting server from DB: {e}")
    finally:
        conn.close()