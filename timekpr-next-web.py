import main
import conf, re, os
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException
from flask import Flask, render_template, request, send_from_directory, redirect

app = Flask(__name__)


def validate_request(computer, user):
    if computer not in conf.trackme:
        return {'result': "fail", "message": "computer not in config"}
    if user not in conf.trackme[computer]:
        return {'result': "fail", "message": "user not in computer in config"}
    else:
        return {'result': "success", "message": "valid user and computer"}


@app.route("/config")
def config():
    return main.get_config()


@app.route("/get_usage/<computer>/<user>")
def get_usage(computer, user):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    usage = main.get_usage(user, computer, ssh)
    return {'result': usage['result'], "time_left": usage['time_left'], "time_spent": usage['time_spent']}, 200


@app.route("/increase_time/<computer>/<user>/<seconds>")
def increase_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    if main.increase_time(seconds, ssh, user):
        usage = main.get_usage(user, computer, ssh)
        return {'result': "success", "time_left": usage['time_left'], "time_spent": usage['time_spent']}, 200
    else:
        return {'result': "fail"}, 500


@app.route("/decrease_time/<computer>/<user>/<seconds>")
def decrease_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer)
    if main.decrease_time(seconds, ssh, user):
        usage = main.get_usage(user, computer, ssh)
        return {'result': "success", "time_left": usage['time_left'], "time_spent": usage['time_spent']}, 200
    else:
        return {'result': "fail"}, 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico',mimetype='image/vnd.microsoft.icon')

## User Config

def update_config(option):
    current_value = main.config.getboolean('Settings', option)
    new_value = not current_value
    main.config.set('Settings', option, str(new_value))
    with open('user_config.ini', 'w') as config_file:
        main.config.write(config_file)

@app.route('/')
def index():
    # Load with settings from user_config.ini
    option1_value = main.config.getboolean('Settings', 'Option1')
    option2_value = main.config.getboolean('Settings', 'Option2')
    option3_value = main.config.getboolean('Settings', 'Option3')
    # Add more options as necessary
    return render_template(
        'index.html',
        option1=option1_value,
        option2=option2_value,
        option3=option3_value
        )

@app.route('/update_config', methods=['POST'])
def update_config_route():
    option = request.form.get('option')
    if option:
        print(f"Updating {option}")
        update_config(option)
        return {'result': "success"}, 200
    else:
        return {'result': "error", 'message': "Option not provided"}, 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
