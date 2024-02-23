import main
import conf, re, os
import configparser
import socket ## ssh error handling
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError ## ssh error handling
from fabric import Connection
from flask import Flask, render_template, request, send_from_directory, redirect, jsonify

### threading
import threading
import time
### threading

app = Flask(__name__)

#### threading

# Create a threading event that can be set or cleared to control the loop
background_service_event = threading.Event()

def check_connection():
    while background_service_event.is_set():
        config = configparser.ConfigParser()
        config.read('database.ini')
        
        # Now the loop checks the event instead of the config file
        trackme_config = main.get_config()
        
        for computer, userArrays in trackme_config.items():
            for users in userArrays:  # More than one user on one device
                user = users[0]  # Use only first value in array = use user and ignore alias
                ssh = None
                try:
                    ssh = main.get_connection(computer)
                except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
                    print(f"No connection to {computer}: {e}")
                finally:
                    if ssh:
                        update_userinfo(ssh, computer, user)
                        main.process_pending_time_changes(ssh, computer)
                        ssh.close()  # Ensure the connection is closed after each attempt

        time.sleep(30)  # Waiting time between checks

def start_background_service():
    if not background_service_event.is_set():
        background_service_event.set()
        t = threading.Thread(target=check_connection)
        t.daemon = True
        t.start()
        print("Background service started.")

def stop_background_service():
    if background_service_event.is_set():
        background_service_event.clear()
        print("Background service stopped.")

#### threading

def validate_request(computer, user):
    if computer not in conf.trackme:
        return {'result': "fail", "message": "computer not in config"}
    # Check if any sublist in the list for the computer contains the user
    if not any(user in userArray for userArray in conf.trackme[computer]):
        return {'result': "fail", "message": "user not in computer in config"}
    else:
        return {'result': "success", "message": "valid user and computer"}

def update_userinfo(ssh, computer, user):
    try:
        timekpra_userinfo_output = str(ssh.run(
            conf.ssh_timekpra_bin + ' --userinfo ' + user,
            hide=True
        ))
        main.save_to_ini(user, computer, timekpra_userinfo_output)
    except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
        error_message = str(e)
        print(f"Failed to update userinfo for {user} on {computer}: {error_message}")
        return {'result': "fail", 'message': error_message}
    else:
        print(f"Userinfo updated successfully for {user} on {computer}")
        return {'result': "success", 'message': "Userinfo updated successfully"}

def update_all_userinfo():
    for computer, userArrays in conf.trackme.items():
        for users in userArrays:
            user = users[0]  # Use only first value in array = use user and ignore alias
            ssh = None
            try:
                ssh = main.get_connection(computer)
                result = update_userinfo(ssh, computer, user)
                # Handle the result if necessary
            except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
                print(f"Failed to update info for {user} on {computer}: {e}")
            finally:
                if ssh:
                    ssh.close()  # Ensure the SSH connection is closed

@app.route("/config")
def config():
    return main.get_config()


@app.route("/get_usage/<computer>/<user>")
def get_usage(computer, user):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    try:
        main.get_connection(computer) ## if connection successfull, update database.ini
    except Exception as e:
        print(f"SSH Error: {e}")
    usage = main.get_usage(user, computer)  ## if no connection, use saved data
    ### Debug
    print(f"{__file__} {__name__}: {usage}")
    return usage, 200


### New save time changes to database.ini

@app.route("/queue_time_change", methods=['POST'])
def queue_time_change():
    try:
        data = request.form
        user = data['user']
        computer = data['computer']
        action = data['action']
        seconds = data['seconds']
        status = data['status']
        
        # Save to database.ini with status 'pending'
        main.queue_time_change(user, computer, action, seconds, status)
        return {'result': "queued"}, 200
    except Exception as e:
        print("Error processing request:", e)
        # Hier können Sie eine detailliertere Fehlermeldung zurückgeben
        return {'error': str(e)}, 400

### New save time changes to database.ini


@app.route("/increase_time/<computer>/<user>/<seconds>")
def increase_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    if main.increase_time(seconds, ssh, user): # Call inscrease_time
        update_userinfo(computer, user)  # Aktualisiere die timekpra_userinfo_output
        usage = main.get_usage(user, computer)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route("/decrease_time/<computer>/<user>/<seconds>")
def decrease_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    if main.decrease_time(seconds, ssh, user): # Call decrease_time
        update_userinfo(computer, user)  # Aktualisiere die timekpra_userinfo_output
        usage = main.get_usage(user, computer)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico',mimetype='image/vnd.microsoft.icon')


# Funktion zum Lesen der gesamten INI-Datei
def read_database_ini():
    database = configparser.ConfigParser()
    database.read('database.ini')
    # Template variables are case sensitive so we make sure sections and keys are lowercase
    normalized_database = {section.lower(): {key.lower(): value for key, value in database.items(section)} for section in database.sections()}
    return normalized_database


@app.route('/')
def index():
    database = read_database_ini()
    return render_template('index.html', database=database)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    print('Received form data:', request.form)
    option = request.form.get('option')
    value = request.form.get('value')
    
    # Check if the required data is present
    if not option or value is None:
        print('Missing data in request!')
        return "Missing data", 400

    # Log the update
    print(f'Updating option {option} to {value}')

    # Read the current settings from the configuration file
    database = configparser.ConfigParser()
    database.read('database.ini')
    # Set the new value for the specified option
    database.set('settings', option, value)

    # Write the updated configuration back to the file
    with open('database.ini', 'w') as configfile:
        database.write(configfile)

    # Check if the updated option is 'background_service' and start/stop the service accordingly
    if option == 'background_service':
        if value == 'true':
            start_background_service()
        elif value == 'false':
            stop_background_service()
        
    # Return a JSON response with the updated setting
    return jsonify({option: value})




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
