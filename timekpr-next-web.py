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
def check_connection():
    while True:
        trackme_config = main.get_config()
        
        for computer, users in trackme_config.items():
            for user in users:
                try:
                    ssh = main.get_connection(computer)
                except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
                    print(f"No connection to {computer}: {e}")
                    continue
                    
                update_userinfo(computer, user)

        time.sleep(30)
#### threading

def validate_request(computer, user):
    if computer not in conf.trackme:
        return {'result': "fail", "message": "computer not in config"}
    if user not in conf.trackme[computer]:
        return {'result': "fail", "message": "user not in computer in config"}
    else:
        return {'result': "success", "message": "valid user and computer"}

def update_userinfo(computer, user):
    try:
        ssh = main.get_connection(computer)
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
    for computer, users in conf.trackme.items():
        for user in users:
            result = update_userinfo(computer, user)


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


@app.route("/increase_time/<computer>/<user>/<seconds>")
def increase_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    if main.increase_time(seconds, ssh, user):
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
    if main.decrease_time(seconds, ssh, user):
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
    return database

# Funktion zum Schreiben der gesamten INI-Datei
def write_database_ini(database):
    with open('database.ini', 'w') as configfile:
        database.write(configfile)

@app.route('/')
def index():
    database_read = read_database_ini()
    # Konvertieren Sie die Konfiguration in ein Dictionary für das Template
    database = {section: dict(database_read[section]) for section in database_read.sections()}
    return render_template('index.html', database=database)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    print('Received form data:', request.form)
    option = request.form.get('option')
    value = request.form.get('value')
    
    if not option or value is None:
        print('Missing data in request!')
        return "Missing data", 400

    print(f'Updating option {option} to {value}')
    value = value.lower() == 'true'
    database = read_database_ini()
    database.set('Settings', option, str(value))
    write_database_ini(database)
    
    return jsonify({option: value})


#### threading

def start_threading():
    t = threading.Thread(target=check_connection)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=8080)

#### threading


if __name__ == "__main__":
    start_threading()
