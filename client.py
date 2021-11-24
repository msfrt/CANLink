import socket
import ssl
import time
import numpy as np
import json
import pprint

from datatransfer import send, recv

HOST = 'data.msuformularacing.com'      # The server's hostname or IP address
PORT = 6969                             # The port used by the server
datakey = "sr22"                        # used to query data specific to this datakey



context = ssl.create_default_context()  # ssl context (TCP works fine here)


conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=HOST)
conn.connect((HOST, PORT))


json_data = {"datakey": datakey}
send(conn, json_data)

json_data = recv(conn)

print(json_data)






