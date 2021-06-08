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
   
## Examples
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