import sqlite3
import docker
from auth_utils import get_db_connection

DATABASE_PATH = 'aklizDB.sqlite'

def add_server_to_db(server_name, memory, user_id):
    conn = get_db_connection()
    try:
        existing_server = conn.execute('SELECT * FROM Servers WHERE name = ?', (server_name,)).fetchone()
        if existing_server:
            return False, "Server name already exists."

        conn.execute('INSERT INTO Servers (name, memory) VALUES (?, ?)', (server_name, memory))
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

import docker

def get_container_port(container_name):
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        if container.status == "running":
            ports = container.attrs['NetworkSettings']['Ports']
            if '25565/tcp' in ports and ports['25565/tcp']:
                return ports['25565/tcp'][0]['HostPort']
            else:
                return "Unknown"
        else:
            return "N/A"
    except docker.errors.NotFound:
        return "N/A"
    except Exception as e:
        print(f"Error fetching port for container {container_name}: {e}")
        return "Unknown"
