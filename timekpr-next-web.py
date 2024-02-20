import main
import conf, re, os
import configparser
import time
import threading
from main import get_config
from main import get_connection
from main import save_to_ini
from main import config
from main import get_database
from main import get_usage
from main import increase_time
from main import decrease_time
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import NoValidConnectionsError
from flask import Flask, render_template, request, send_from_directory, redirect

app = Flask(__name__)

def check_connection():
  while True:
    trackme_config = get_config()
    
    for computer, users in trackme_config.items():
      for user in users:
      
        try:
          ssh = get_connection(computer)
        
        except NoValidConnectionsError as e:
          print(f"No connection to {computer}")
          continue
          
        try:
          timekpra_userinfo_output = str(ssh.run(
                    conf.ssh_timekpra_bin + ' --userinfo ' + user,
                    hide=True
                ))
          save_to_ini(user, computer, timekpra_userinfo_output)
          
        except:
          print(f"Error getting data for user {user} on {computer}")
          continue
          
      
    time.sleep(30)

def validate_request(computer, user):
    if computer not in conf.trackme:
        return {'result': "fail", "message": "computer not in config"}
    if user not in conf.trackme[computer]:
        return {'result': "fail", "message": "user not in computer in config"}
    else:
        return {'result': "success", "message": "valid user and computer"}


@app.route("/config")
def config():
    return get_config()


@app.route("/get_usage/<computer>/<user>")
def get_usage(computer, user):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    usage = get_usage(user, computer)
    ### Debug
    print(f"{__file__} {__name__}: {usage}")
    return usage, 200


@app.route("/increase_time/<computer>/<user>/<seconds>")
def increase_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = get_connection(computer)
    if increase_time(seconds, ssh, user):
        usage = get_usage(user, computer, ssh)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route("/decrease_time/<computer>/<user>/<seconds>")
def decrease_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = get_connection(computer)
    if decrease_time(seconds, ssh, user):
        usage = get_usage(user, computer, ssh)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico',mimetype='image/vnd.microsoft.icon')

## User Config

def update_config(option):
    current_value = config.getboolean('Settings', option)
    new_value = not current_value
    config.set('Settings', option, str(new_value))
    with open('database.ini', 'w') as config_file:
        config.write(config_file)

@app.route('/')
def index():
    config = get_database()
    print(f"Settings for index.html {config}")
    # Load with settings from database.ini
    option1_value = config.getboolean('Settings', 'option1')
    option2_value = config.getboolean('Settings', 'option2')
    option3_value = config.getboolean('Settings', 'option3')
    # Add more options as necessary
    context = {
    "option1": option1_value,
    "option2": option2_value,
    "option3": option3_value
    }
    return render_template('index.html', **context)

@app.route('/update_config', methods=['POST'])
def update_config_route():
    option = request.form.get('option')
    if option:
        print(f"Updating {option}")
        update_config(option)
        return {'result': "success"}, 200
    else:
        return {'result': "error", 'message': "Option not provided"}, 400

def main():
    t = threading.Thread(target=check_connection)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
