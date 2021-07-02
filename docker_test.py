import docker
import time
client_local = docker.from_env()
client_remote = docker.DockerClient(base_url='ssh://ydebock@143.129.83.93', use_ssh_client=False)

client = client_remote

# container = client.containers.run(image='gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration', ports={'5556/tcp': 5556},
#                            environment={'LENGTH': 1200, 'tickspersecond': 1, 'IP_PYTHON': '143.129.83.94', 'separate_ra': 0},
#                            hostname='docker-simulation.localdomain', auto_remove=True, detach=True, name='dynamicsim')

container = client.containers.run(image='gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:counter_in_json',
                           environment={'LENGTH': 1200, 'tickspersecond': 1, 'IP_PYTHON': '143.129.83.94', 'separate_ra': 0},
                           network='host', auto_remove=True, detach=True)





