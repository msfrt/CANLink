#!/bin/python3

from flask import Flask, render_template
from flask_basicauth import BasicAuth
from flask_socketio import SocketIO, emit
import os
import re

import socket
import ssl

import can
import cantools

# import thread module for car clients
from _thread import *
import threading

# custom functions allow for the sending and recieving of json data
from datatransfer import send, recv


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# username and password
app.config['BASIC_AUTH_USERNAME'] = 'msu'
app.config['BASIC_AUTH_PASSWORD'] = 'green'
app.config['BASIC_AUTH_FORCE'] = False  # require auth for every page
basic_auth = BasicAuth(app)

# links to SSL keys
CHAIN_PEM = "ssl/fullchain.pem"
PRIVATE_KEY = "ssl/privkey.pem"

# for the car connections, NOT the flask webserver
CAR_CONNECT_HOST = ''           # any host - localhost or external
CAR_CONNECT_PORT = 6969         # Port to listen on (non-privileged ports are > 1023)


app.config['TESTING'] = True
app.config['ENV'] = "development"
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True


# utility functions -----------------------------------------------------------

def handshake_then_die(conn, return_ip=False):
    """
    This function, appropriately, does what it says! It handshakes the
    currently active connection, then closes it (since the car client creates
    a new connection for every transaction). It resturns true if the handshake
    was good (that means there's a decent connection)
    @param conn - the connection object
    @param return_ip bool - if set to true, the function will return the
        connection's ip address.
    @returns boolean - True if the connection is good, False if no connection
    """

    if conn is None:
        return False

    try:
        send(conn, "handshake")

        # set the socket to wait for one second before giving up
        conn.settimeout(1.0)
        return_val = recv(conn)

        ip = conn.getpeername()

        # done with the socket, we can close it now
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()

        # if good, return the ip or True
        if return_val == True:
            return ip if return_ip else True

    except Exception as e:
        # some sort of error
        print("There was some sort of error when pinging the client: " + str(e))
        pass

    return False


# index page ------------------------------------------------------------------

# find all of the vehicle pages that we can link to. This will automatically
# find HTML files in templates/vehicles/ and then create a link to them
# on the homepage
vehicles = [filename[0:-5] for filename in os.listdir("templates/vehicles")]
vehicles_online_dict = {}
for v in vehicles:
    vehicles_online_dict[v] = False

@app.route("/")
def landing_page():

    # determine what vehicles are currently online here
    vehicles_online_dict["sr22"] = handshake_then_die(CAR_CONNECT_DICT[SR22_KEY])

    return render_template("landing.html", vehicles=vehicles_online_dict)


# s22 page --------------------------------------------------------------------

# file paths to vehicle dbcs. Note, if these are not downloaded after cloning
# the CANLink repo, cd into Electrical-SR20, then run `git submodule init` and
# then `git submodule update`
SR22_DBC_CAN1_FILEPATH = "/home/sparty/Electrical-SR20/DBCs/CAN1.dbc"
SR22_DBC_CAN2_FILEPATH = "/home/sparty/Electrical-SR20/DBCs/CAN2.dbc"


# loads the dbc files into actual objects
sr22_dbc_can1 = cantools.database.load_file(SR22_DBC_CAN1_FILEPATH)
sr22_dbc_can2 = cantools.database.load_file(SR22_DBC_CAN2_FILEPATH)


# this will hold all of the current values for all inputs on the page.
# when inputs are changed on the page, their respective entries are updated here
# then all changes are propogated to other clients.
sr22_current_values = dict()

# renders the page template
@app.route("/sr22")
def sr22_page():
    return render_template("vehicles/sr22.html", vehicles=vehicles)

# called on page load
@socketio.on('sr22_connected')
def handle_my_custom_event(json):
    print('received json: ' + str(json))


# called to check the vehicle status
@socketio.on('sr22_computerStatusRefresh')
def sr22_vehicle_status(json):
    print('received vehicle status request!')
    ip = handshake_then_die(CAR_CONNECT_DICT[SR22_KEY], return_ip=True)
    emit('sr22_computerStatus', ip)


# called on driverMessageSend
@socketio.on('sr22_driverMessageSend')
def handle_driver_message_send(json):
    #print('received json: ' + str(json))

    # create an empty dict with the actual signal names from the DBC
    data_dict = {"USER_driverMessageChar" + str(i): 0 for i in range(0, 8)}
    
    # if there was a character input, convert it to it's ascii value with ord()
    for input_name, char in json.items():
        if char != '':
            signal_name = "USER_driverMessageChar" + str(int(input_name[-1])-1)
            data_dict[signal_name] = ord(char)

    # driver display message
    msg = sr22_dbc_can2.get_message_by_name("USER_12")

    # raw can stuff, ready to send!
    msg_id = msg.frame_id
    msg_data_encoded = msg.encode(data_dict)
    msg_data_encoded_list = [int(byte) for byte in msg_data_encoded]
    print(msg_data_encoded_list)

    # returns a list of messages to send (although this is a single message, we
    # aim to keep the formatting consistant)
    return_data = [{"bus":"can2", "id":msg_id, "data": msg_data_encoded_list}]

    # get the open socket
    conn = CAR_CONNECT_DICT[SR22_KEY]

    if conn is not None:
        # send the message data
        send(conn, return_data)

        conn.shutdown(socket.SHUT_RDWR)
        conn.close()

        CAR_CONNECT_DICT[SR22_KEY] = None

    else:

        print("Car is not connected!")




# called on driverLEDSend
@socketio.on('sr22_driverLEDSend')
def handle_driver_led_send(json):
    print('received json: ' + str(json))


# s23 page --------------------------------------------------------------------
@app.route("/sr23")
def sr23_page():
    return render_template("vehicles/sr23.html", vehicles=vehicles)


# car-connect -----------------------------------------------------------------

# this dictionary will hold the car keys, then their connection objects. You
# should add every potential connection to this dictionary in the form of
# {"key_name": None}, as when a connection is made, the key will be checked
# to see if this is an actual connection, or some malicious connection. For a
# valid connection, the dict will look like this: 
# {"datakey": conn_obj }
SR22_KEY = "sr22"
CAR_CONNECT_DICT = {SR22_KEY: None, "othercar_key": None}

def car_connect_listener():
    """
    This function acts *almost* like an entirely different program. It has a
    loop that listens for incoming socket connections from cars. When the
    connections are made, it calls the handler thread to store the connections
    """
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((CAR_CONNECT_HOST, CAR_CONNECT_PORT))
        sock.listen(5)

        # TLS server context - load public and private keys generated
        # by Let's Encrypt
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CHAIN_PEM, PRIVATE_KEY)

        # wrap the unsecure socket in TLS
        with context.wrap_socket(sock, server_side=True) as ssock:
            
            while True:
                conn, addr = ssock.accept()  # accepts conn like regular socket

                # start a new thread to handle this connection
                params = (conn, addr)
                start_new_thread(accept_car_connection, params)


def accept_car_connection(conn, addr):
    """
    Accepts the connection, verifies that it's from a valid source, then
    stores it for later use
    """
    
    # read the data
    json = recv(conn)

    print(f"{addr} : {json}")

    # make sure that the datakey was sent!
    try:
        datakey = json["datakey"]
    except KeyError:
        # bad connection
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        return

    # if there's new valid connection
    if datakey in CAR_CONNECT_DICT.keys():
        

        # if there's alredy a connection there, try to end it and replace it
        # with this new, fresh, and clean one
        if CAR_CONNECT_DICT[datakey] is not None:

            # try to end it
            try:
                CAR_CONNECT_DICT[datakey].shutdown(socket.SHUT_RDWR)
                CAR_CONNECT_DICT[datakey].close()

            # some weird error with the socket. ANyways, continue fresh
            except:
                pass

            # set to None to delete the object
            finally:
                CAR_CONNECT_DICT[datakey] = None

        # add the new connection
        CAR_CONNECT_DICT[datakey]= conn


        print(CAR_CONNECT_DICT)

    # if the connection is invalid
    else:
        return
        




if __name__ == '__main__':

    # launch a new thread into the server_client_main function
    params = ()
    start_new_thread(car_connect_listener, params)

    ssl_context = (CHAIN_PEM, PRIVATE_KEY)
    socketio.run(app=app, host='0.0.0.0', ssl_context=ssl_context)










    