import socket
import ssl
import time
import numpy as np
import json
import pprint

import can
import cantools

"""
This application is very simple. It essentially just establishes a connection
with the server, then waits for a response with CAN data. No encoding or
decoding is necessary, it just sends the data over CAN.
"""

from datatransfer import send, recv

HOST = 'data.msuformularacing.com'      # The server's hostname or IP address
PORT = 6969                             # The port used by the server
datakey = "sr22"                        # used to query data specific to this datakey

# the CAN channels are inverted on SR22 for whatever reason
can1 = can.interface.Bus(bustype="socketcan", channel="can1")
can2 = can.interface.Bus(bustype="socketcan", channel="can0")


context = ssl.create_default_context()  # ssl context (TCP works fine here)

while True:
    with context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=HOST) as conn:

        try:
            conn.connect((HOST, PORT))
        
        except ConnectionRefusedError as e:
            print("A connection could not be made! Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            continue

        print("A connection was made!")

        # send the data key to let the server know who we are
        json_data = {"datakey": datakey}
        send(conn, json_data)

        # this call blocks until the server sends back message(s)
        json_data = recv(conn)
        print(json_data)

        # iterates through every message that the server returned
        for msg_info in json_data:

            try:
                bus_name = msg_info["bus"]
                msg_id = msg_info["id"]
                msg_data = msg_info["data"]

            except KeyError as e:
                print("There was an error decoding the server's message: " + e)
                continue

            # print(bus_name)
            # print(msg_id)
            # print(msg_data)
            
            # creates the message object that can be sent
            msg = can.Message(arbitration_id=msg_id, data=msg_data, is_extended_id=False)

            if bus_name == "can1":
                can1.send(msg)
            elif bus_name == "can2":
                can2.send(msg)



        






