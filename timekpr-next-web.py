import main
import conf, re, os
import configparser
from fabric import Connection
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
    try:
        main.get_connection(computer, user) ## if connection successfull, update database.ini
    except Exception as e:
        print(f"SSH Error: {e}")
    usage = main.get_usage(user, computer)
    ### Debug
    print(f"{__file__} {__name__}: {usage}")
    return usage, 200


@app.route("/increase_time/<computer>/<user>/<seconds>")
def increase_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer, user)
    if main.increase_time(seconds, ssh, user):
        usage = main.get_usage(user, computer, ssh)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route("/decrease_time/<computer>/<user>/<seconds>")
def decrease_time(computer, user, seconds):
    if validate_request(computer, user)['result'] == "fail":
        return validate_request(computer, user), 500
    ssh = main.get_connection(computer, user)
    if main.decrease_time(seconds, ssh, user):
        usage = main.get_usage(user, computer, ssh)
        return usage, 200
    else:
        return {'result': "fail"}, 500


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico',mimetype='image/vnd.microsoft.icon')

## User Settings

#ToDo: Änderung der Einstellungen überschreibt die ganze database.ini
def update_settings(option):
    current_value = main.database.getboolean('Settings', option)
    new_value = not current_value
    main.database.set('Settings', option, str(new_value))
    with open('database.ini', 'w') as database_file:
        main.database.write(database_file)

@app.route('/')
def index():
    # Load with settings from database.ini
    option1_value = main.database.getboolean('Settings', 'Option1')
    option2_value = main.database.getboolean('Settings', 'Option2')
    option3_value = main.database.getboolean('Settings', 'Option3')
    # Add more options as necessary
    return render_template(
        'index.html',
        option1=option1_value,
        option2=option2_value,
        option3=option3_value
        )

@app.route('/update_settings', methods=['POST'])
def update_settings_route():
    option = request.form.get('option')
    if option:
        print(f"Updating {option}")
        update_settings(option)
        return {'result': "success"}, 200
    else:
        return {'result': "error", 'message': "Option not provided"}, 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
