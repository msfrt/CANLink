from flask import Flask, render_template
from flask_basicauth import BasicAuth
from flask_socketio import SocketIO, emit
import os
import re

import can
import cantools

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


app.config['TESTING'] = True
app.config['ENV'] = "development"
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True


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

    # determine what vehicles are currently online HERE

    return render_template("landing.html", vehicles=vehicles_online_dict)


# s22 page --------------------------------------------------------------------

# file paths to vehicle dbcs. Note, if these are not downloaded after cloning
# the CANLink repo, cd into Electrical-SR20, then run `git submodule init` and
# then `git submodule update`
SR22_DBC_CAN1_FILEPATH = "Electrical-SR20/DBCs/CAN1.dbc"
SR22_DBC_CAN2_FILEPATH = "Electrical-SR20/DBCs/CAN2.dbc"


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


# called on driverMessageSend
@socketio.on('sr22_driverMessageSend')
def handle_driver_message_send(json):
    print('received json: ' + str(json))


# called on driverLEDSend
@socketio.on('sr22_driverLEDSend')
def handle_driver_led_send(json):
    print('received json: ' + str(json))


# s23 page --------------------------------------------------------------------

@app.route("/sr23")
def sr23_page():
    return render_template("vehicles/sr23.html", vehicles=vehicles)


if __name__ == '__main__':
    ssl_context = (CHAIN_PEM, PRIVATE_KEY)
    socketio.run(app=app, host='0.0.0.0', ssl_context=ssl_context)










    