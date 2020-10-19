# DynamicSim_AI

1) Clone this git repository to the server

2) Install the necessary packages from the requirements.txt file:

    `pip3 install -r requirements.txt
`
3) When the proto file is updated, execute the following command to generate the python code:

    `protoc -I=. --python_out=. x.proto`

python3 CommunicationRA.py

python3 CommunicationRO.py
