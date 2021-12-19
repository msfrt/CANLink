import json

ENCODING_METHOD = "utf-8"  # utf-8 is pretty good. better than ascii

def send(s, json_data):
    """
    Takes an ssl secure socket and string data to send.
    @param s - the socket object that's already established a connection
    @param json_data - the data that you want to send in the form of a json-able type, like a dicitonary (JSON)
    @returns None
    """

    # turns dict into string and encodes it into bytes
    json_bstr = json.dumps(json_data).encode(ENCODING_METHOD)
    json_len = len(json_bstr)

    # send the message length only in the first send
    s.sendall(str(json_len).encode(ENCODING_METHOD))

    # send the json
    s.sendall(json_bstr)


def recv(s):
    """
    Listens to the socket and recieves the string data sent by the send function
    @param s - the socket object that's already established a connection
    @returns json_data - the JSON that was sent decoded into pythonic form
    """

    # first thing recieved should be the length
    data = s.recv(1024)
    json_len = int(str(data.decode(ENCODING_METHOD)))

    data_total = None  # we will store the entire bytestring here

    # read while there's still stuff to be read
    while json_len > 0:

        data = s.recv(1024)  # read raw data from the socket
        
        json_len -= len(data)

        if not data_total:
            data_total = data
        else:
            data_total += data

    # Decode bytestring and turn into a python object
    json_str = data_total.decode(ENCODING_METHOD)
    json_data = json.loads(json_str)

    return json_data
