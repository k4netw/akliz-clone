import sqlite3  # for database operations
import string  # for generating RCON passwords
import docker  # for Docker operations
from auth_utils import get_db_connection  # shared utility for database connection
from flask_socketio import emit  # for real-time log streaming
import random  # for random password generation

DATABASE_PATH = 'aklizDB.sqlite'  # database file path

client = docker.from_env()  # initialize Docker client

rcon_connections = {}  # store active RCON connections

def generate_rcon_password(length=16):  # generates a random RCON password
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))  # generate random password

def add_server_to_db(server_name, memory, user_id):  # adds a new server to the database
    conn = get_db_connection()
    try:
        existing_server = conn.execute('SELECT * FROM Servers WHERE name = ?', (server_name,)).fetchone()
        if existing_server:  # check if server name already exists
            return False, "Server name already exists."

        rcon_password = generate_rcon_password()  # create RCON password

        conn.execute(  # add server to database
            'INSERT INTO Servers (name, memory, rcon_password) VALUES (?, ?, ?)',
            (server_name, memory, rcon_password)
        )
        server_id = conn.execute('SELECT id FROM Servers WHERE name = ?', (server_name,)).fetchone()['id']
        conn.execute('INSERT INTO UserServers (userID, serverID) VALUES (?, ?)', (user_id, server_id))
        conn.commit()
        return True, "Server added successfully."
    except sqlite3.Error as e:  # handle database errors
        return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def create_docker_container(server_name, memory):  # creates a new Docker container for the server
    try:
        container = client.containers.run(  # create a Docker container
            image="itzg/minecraft-server",
            name=server_name,
            detach=True,
            environment={
                "EULA": "TRUE",  # accept Mojang's EULA
                "MEMORY": f"{memory}M"  # set memory limit
            },
            ports={'25565/tcp': None}  # expose Minecraft port
        )
        return True, f"Docker container '{server_name}' created successfully."
    except docker.errors.DockerException as e:  # handle Docker errors
        return False, f"Docker error: {str(e)}"

def get_user_servers(user_id):  # retrieves all servers associated with a user
    conn = get_db_connection()
    try:
        query = '''
            SELECT Servers.id, Servers.name, Servers.memory
            FROM Servers
            INNER JOIN UserServers ON Servers.id = UserServers.serverID
            WHERE UserServers.userID = ?
        '''  # fetch user's servers
        servers = conn.execute(query, (user_id,)).fetchall()
        return [dict(server) for server in servers]  # return list of servers as dictionaries
    finally:
        conn.close()

def get_container_port(server_name):  # retrieves the mapped port of a Docker container
    try:
        container = client.containers.get(server_name)
        ports = container.attrs['NetworkSettings']['Ports']
        if ports and '25565/tcp' in ports and ports['25565/tcp']:
            return ports['25565/tcp'][0]['HostPort']  # return mapped port
        else:
            return "Unknown"
    except docker.errors.NotFound:  # handle missing container
        return "Not Found"
    except Exception as e:
        return f"Error: {str(e)}"

def get_server_details(server_id):  # retrieves details for a specific server
    conn = get_db_connection()
    try:
        query = '''
            SELECT Servers.id, Servers.name, Servers.memory
            FROM Servers
            WHERE Servers.id = ?
        '''  # fetch server details
        server = conn.execute(query, (server_id,)).fetchone()
        if not server:  # check if server exists
            raise ValueError(f"Server with ID {server_id} not found.")

        server = dict(server)
        server['port'] = get_container_port(server['name'])  # get port mapping
        server['version'] = "1.21.4"  # hardcoded version
        server['region'] = "Europe"  # hardcoded region
        return server
    finally:
        conn.close()

def stream_logs(server_name):  # streams live logs from a Docker container
    try:
        container = client.containers.get(server_name)  # fetch container
        for line in container.logs(stream=True, tail=10):  # stream logs
            emit('server_log', {'log': line.decode('utf-8').strip()})
    except Exception as e:  # handle logging errors
        emit('server_log', {'log': f'[ERROR]: {str(e)}'})

def start_container(server_name):  # starts a Docker container
    try:
        container = client.containers.get(server_name)  # fetch container
        container.start()  # start the container
        return True
    except docker.errors.NotFound:  # handle missing container
        return False

def stop_container(server_name):  # stops a running Docker container
    try:
        container = client.containers.get(server_name)  # fetch container
        container.stop()  # stop the container
        return True
    except docker.errors.NotFound:
        return False

def restart_container(server_name):  # restarts a Docker container
    try:
        container = client.containers.get(server_name)  # fetch container
        container.restart()  # restart the container
        return True
    except docker.errors.NotFound:
        return False

def remove_docker_container(container_name):  # removes a Docker container
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()  # remove the container
        print(f"Successfully removed container: {container_name}")
    except docker.errors.NotFound:
        print(f"Container {container_name} not found!")
    except Exception as e:
        print(f"Error while removing container {container_name}: {str(e)}")

def remove_server_from_db(server_id):  # removes a server from the database
    conn = sqlite3.connect('aklizDB.sqlite')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM UserServers WHERE serverID=?", (server_id,))
        cursor.execute("DELETE FROM Servers WHERE id=?", (server_id,))  # remove server records
        conn.commit()
        print(f"Server with ID {server_id} deleted from both UserServers and Servers.")
    except sqlite3.Error as e:  # handle database errors
        print(f"Error while deleting server from DB: {e}")
    finally:
        conn.close()
