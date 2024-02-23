import main  # Access functions from main.py
from flask import Flask, render_template, request, jsonify, send_from_directory  # Flask-related functionality
import configparser  # Used for reading and writing 'database.ini' within the update_settings function
import os  # Used to locate the 'favicon.ico' file within the static directory

app = Flask(__name__)

@app.route("/config")
def config():
    return main.get_config()

@app.route("/get_usage/<computer>/<user>")
def get_usage(computer, user):
    if main.validate_request(computer, user)['result'] == "fail":
        return main.validate_request(computer, user), 500
    try:
        main.update_all_userinfo() ## if connection successfull, update database.ini
    except Exception as e:
        print(f"SSH Error: {e}")
    usage = main.get_usage(user, computer)  ## if no connection, use saved data
    # print(f"{__file__} {__name__}: {usage}")
    return usage, 200

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
            main.start_background_service()
        elif value == 'false':
            main.stop_background_service()
        
    # Return a JSON response with the updated setting
    return jsonify({option: value})

#### Give database.ini to web frontend Start #####

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

#### Give database.ini to web frontend End #####


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico',mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
