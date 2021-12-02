#!/usr/bin/env python3

import socket
import ssl

import json

# import thread module
from _thread import *
import threading

from datatransfer import send, recv

CERTCHAIN_PEM = "/etc/letsencrypt/live/data.msuformularacing.com/fullchain.pem"
PRIVATE_KEY = "/etc/letsencrypt/live/data.msuformularacing.com/privkey.pem"


HOST = ''           # any host - localhost or external
PORT = 6969         # Port to listen on (non-privileged ports are > 1023)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, PORT))
        sock.listen(5)

        # TLS server context - load public and private keys generated
        # by Let's Encrypt
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERTCHAIN_PEM, PRIVATE_KEY)

        # wrap the unsecure socket in TLS
        with context.wrap_socket(sock, server_side=True) as ssock:
            
            while True:
                conn, addr = ssock.accept()  # accepts conn like regular socket

                # start a new thread to handle this connection
                params = (conn, addr)
                start_new_thread(accept_connection, params)



def accept_connection(conn, addr):
    """
    @param conn - the connection object
    @param addr - the address of the connecting party
    This function is called everytime a new thread is created. The function
    "becomes" the thread... think of it like another main function.
    """

    with conn:  # automatically closes socket when done


        # read the data
        json = recv(conn)

        print(f"{addr} : {json}")

        # example_db = {
        #     "sr20": [{"bus": "can1", "id":  0x69, "data": [0xD, 0xE, 0xA, 0xD, 0xB, 0xE, 0xE, 0xF]}],
        #     "sr22": [{"id": 0x420, "data": [0xD, 0xE, 0xA, 0xD, 0xB, 0xE, 0xE, 0xF]}]
        #     }


        # # get the datakey that the client is reqesting
        # datakey = json["datakey"]

        # send(conn, example_db[datakey])



def setup_database():
    # factory function to create the database table if it doesn't exist yet
    datakey_table = """
CREATE TABLE datakey(

)
"""


if __name__ == "__main__":
    main()
















