# DynamicSim_AI

1) Clone this git repository to the server

2) Install the necessary packages from the requirements.txt file:

    `pip3 install -r requirements.txt
`
3) When the proto file is updated, execute the following command to generate the python code:

    `protoc -I=. --python_out=. x.proto`
   
4) To start the python controller
   
   `python3 CommunicationRO.py` <br>
   `python3 CommunicationRA.py` (when seperate RO and RA)

## Run the simulation via docker from python
To start the simulator in Docker from python, use the following commands:

1) Create Client:

- Docker host same PC as python controller:
  
        import docker
        client = docker.from_env()

- Docker host another PC as python controller:
          
        import docker
        client = docker.DockerClient(base_url='ssh://ydebock@143.129.83.93')
    make sure that both PC have password-less ssh access to each other

2) Start simulator in Docker container:

- To run with network of the host system (preffered):

        client.containers.run(
            image='gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration',
            environment={'LENGTH': 1200, 'tickspersecond': 1, 'IP_PYTHON': '143.129.83.94', 'separate_ra': 0},
            network='host', 
            auto_remove=True, 
            detach=True, 
            name='dynamicsim'
        )
- To run with bridge network:
  
        client.containers.run(
            image='gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration',
            environment={'LENGTH': 1200, 'tickspersecond': 1, 'IP_PYTHON': '143.129.83.94', 'separate_ra': 0},
            hostname='docker-simulation.localdomain',
            ports={'5556/tcp': 5556}
            auto_remove=True, 
            detach=True, 
            name='dynamicsim'
        )
    In this case the simulation takes the ip address of the docker container, like 172.x.x.x. This is no problem when the
python controller and docker container running on the same host machine. However when running both on another host machine,
  the python must set the IP address of the machine running the docker container manually. To change this replace in _CommunicatorRO.py_:

       self._communicator.set_push_socket(message.info.ipaddress)
            
    with
  
       self._communicator.set_push_socket(<<ip address docker machine>>)

More information about the Docker SDK for python: https://docker-py.readthedocs.io/en/stable/

## Examples

For each version (docker and git tag) the examples can differ. So use for both the simulator and controller the same tag to test the examples

Currently we the following tags with corresponding examples:

- server_migration 
- counter_in_json

### Vertical Scaling (_RO_VerticalScaling.py_)

- Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
- This example displays the vertical scaling option (adding more resources to a microservice)
- This example is tested with the 'server_migration' docker image of the simulator
- To use this example, change line 16 of CommunicationRO.py to `self.ro_agent = RO_VerticalScaling(self.timemanager)`


- Each MS two parameters for the vertical scaling: current_thread_limit and maximum_thread_limit

- current_thread_limit: a float bigger than 0. This represents the number of threads the MS can handle at the moment.
   - If the cpu_cycles per tick is 300 and the current_thread_limit is 1.5, the MS can use 450 cpu_cycles per tick
   - This variable can be changed during the lifetime of the MS via an 'UpdateParameterActor' message

- maximum_thread_limit: a float bigger than 0. This represents the maximum number of threads the MS can handle 
  - This value is constant and is set when the MS is created. When the controller sets the current_thread_limit bigger than this value, the limit is maximum_thread_limit

- max_cpu_cycles_per_tick = cpu_cylces_per_tick * min(current_thread_limit, maximum_thread_limit)

#### SCENARIO
- We start to go to one microservice and delete MS_dev2cM5T
- Every 10 ticks we increase the traffic generator number of jobs
- The current_thread_limit is increased when the CPU usage > 0.95 and decreased < 0.5
- The CPU usage is reported with the usage cpu cycles / cpu_cycles_per_tick (300), so the usage can be bigger than 1.0
- For this we divide it in the controller with min(current_thread_limit, maximum_thread_limit)
- The controller is only for testing this feature
- At tick 322 we increase the current_thread_limit to 4.1, but this has no effect on the load because the MS is limited to 4.0

The command of the docker  to test this examples:
- `docker run -it --rm --network host -e LENGTH=1200 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration`

### Horizontal Scaling (_RO_HorizontalScaling.py_)
- Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
- This example displays the horizontal scaling option (adding more servers to host microservices)

- This example is tested with the 'server_migration' docker image of the simulator
- To use this example, change line 16 of CommunicationRO.py to `self.ro_agent = RO_HorizontalScaling(self.timemanager)`


- Each server has a limited amount of resources (in this case CPU resources). To deploy more microservices, we need start a new server.
- Each server has three parameters: cpu_cylces_per_second, number of cores, memory capacity(MB).
- For example: [300, 10, 16000] => In this example the server can process 3000 cpu_cycles per second
- To create a new server, we use the default message (GenericActor) to start an actor (lines 137-145)
- The parameters for the server are created via the 'create_parameter_message' function, which are passed to the server actor
- In the class_ServerActor of the simulator, the parameters are parsed from the array. So, the order is important


#### SCENARIO
- The initial server which start with the simulator has the following paramters: [300, 40, 16000]
- This server will take longer to reach the load of 0.8, before starting a new server
- Every 10 ticks we increase the number of jobs for traffic generator with the right to create a new MS
- When the cpu usage of the server is bigger than 0.8 we start a new server.
- After 600 ticks the load is decreased every 10 ticks.
- When the cpu usage of the server is smaller than 0.5 we delete the last created server and the remaining microservices on it.
- The controller is only for testing this feature

The command of the docker  to test this examples:
- `docker run -it --rm --network host -e LENGTH=1200 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration
`
  
### Server Migration (_RO_ServerMigration.py_)

- Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
- This example displays the server migration of a MS

- This example is tested with the 'server_migration' docker image of the simulator
- To use this example, change line 16 of CommunicationRO.py to `self.ro_agent = RO_ServerMigration(self.timemanager)`

#### EXAMPLE
- Sometimes it is needed to move a MS from one server to another server.
- For example: when two or more MS communicate constantly, they can be better placed on one server,
- Or, when scaling down in MS, the MS on two servers can be combined on one server to shutdown a server


- To migrate a MS, a UpdateParameterActor message is sent to the simulator with reciptient the server running the MS and parameter migrate_service
- The parameters are: the MS name and the server name where the MS should migrate to.
- For now the MS keeps it jobs and is directly migrated to the new server


#### SCENARIO
- A second server is created at tick 5.
- Every 10 ticks the traffic increased so a new MS must be created (no vertical scaling) to handle the traffic
- The new MS is automatically placed on Server_1 (the first server)
- At tick 95 all the active MS (state = RUNNING) are migrated to the new server created at tick 5.
- after this you will see in the prints that the MS are migrated to the new server
- The new MS after 95 will still be placed on Server_1 and the loadbalancer will also stay at Server_1

#### The command of the docker  to test this examples:
` docker run -it --rm --network host -e LENGTH=120 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration
`

### Loadbalancer Weight-based Algorithm (_RO_LoadbalancerWeight.py_)

- Make sure that in the CommunicationRO.py file the handle_message function has both float and string counters (line 35-40).
- This example displays the server migration of a MS

This example is tested with the 'server_migration' docker image of the simulator.
 To use this example, change line 16 of CommunicationRO.py to self.ro_agent = RO_LoadbalancerWeight(self.timemanager)

#### EXAMPLE
- Depending on certian parameters and environments, it is not preferable for the loadbalancer to equally dividing the traffic between the MS
- For example: different servers can result in different processing speeds and thus different jobs per second for each MS
- Or: when a new MS is started, the current MS have a higher load and maybe some overflow, the new MS can handle more traffic at the beginning to restore the load in the current MS faster


- To change the weight of a MS, a UpdateParameterActor message is sent to the simulator with reciptient the loadbalancer and parameter weight.
- The parameters are: the MS name and the new weight for this MS. For each MS a new message is sent, but these messages are automatically bundled in one big message by Communicator.

The loadbalancer adds all the weights and normalize them. Then, it will divide them between MS depending on the normalized weight.

For this we need to set the algorithm of the loadbalancer in the Docker environment via: `-e loadbalancer_algorithm={weighted|equal}`,
(default is equal, so for this the environment must not be set.)

#### SCENARIO
- At tick 1, 8 new MS are started to have a total MS of 10
- We generate each tick the same traffic load
- With an equal load (until tick 5) the load is divide equally between the MS, which results in a load per MS of 0.52
- Every 10 ticks we change the weight randomly for each MS, starting at tick 10.
- After 2 ticks, you will see the result in the loads of the MS which is different for each MS depending on the load.

The command of the docker  to test this examples:
`docker run -it --rm --network host -e LENGTH=120 -e IP_PYTHON=143.129.83.94 -e separate_ra=0 -e loadbalancer_algorithm=weighted gitlab.ilabt.imec.be:4567/idlab-nokia/dynamicsim:server_migration
`