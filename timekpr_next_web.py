# timekpr-next-web.py

import main  # Access functions from main.py
from flask import Flask, render_template, request, jsonify, send_from_directory  # Flask-related functionality
import configparser  # Used for reading and writing 'database.ini' within the update_settings function
import os  # Used to locate the 'favicon.ico' file within the static directory
from datetime import datetime # Used to format timestamps
from conf import pin_required, pin_code

app = Flask(__name__)

@app.route("/config")
def config():
    config_data = main.get_config()
    return jsonify(config_data)

@app.route("/get_database/<computer>/<user>")
def get_database(computer, user):
    # First, validate the request
    validation_result = main.validate_request(computer, user)
    if validation_result['result'] == "fail":
        return validation_result, 500

    # Attempt to establish an SSH connection
    ssh = None
    ssh_success = False  # Initialize a flag to track SSH connection success
    try:
        ssh = main.get_connection(computer)
        if ssh:
            ssh_success = True  # Set the flag to True if SSH connection is successful
            # If the connection is successful, update user info
            main.process_pending_time_changes(computer, ssh)
            main.update_userinfo(ssh, computer, user)
        else:
            # If the connection is not successful, handle it accordingly
            print(f"Could not establish SSH connection to {computer}")
    except Exception as e:
        print(f"SSH Error: {e}")
    finally:
        # Close the SSH connection if it was established
        if ssh:
            ssh.close()

    usage = main.get_database(user, computer)  # Get usage data, either from the updated info or from saved data
    usage['online_status'] = 'Online' if ssh_success else 'Offline'  # Add the online status to the usage data
    print(f"{__file__} {__name__}: {usage}")
    return jsonify(usage), 200

@app.route("/queue_time_change", methods=['POST'])
def queue_time_change():
    try:
        data = request.form
        if pin_required:
            if 'pin' not in data or data['pin'] != pin_code:
                return jsonify({'error': 'Invalid PIN'}), 403
        user = data['user']
        computer = data['computer']
        action = data['action']
        seconds = data['seconds']
        timeframe = data['timeframe']
        status = data['status']
        
        # Call the queue_time_change function and get the result
        result = main.queue_time_change(user, computer, action, seconds, timeframe, status)
        
        # Return the result to the frontend
        return jsonify({'result': result}), 200
    except Exception as e:
        print("Error processing request:", e)
        return jsonify({'error': str(e)}), 400

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

##### Formatting Functions for web frontend Start #####

# Define a custom filter function
## Don't move this to main.py! ##
def format_timestamp(value, format='%Y-%m-%d %H:%M:%S'):
    try:
        # Assume the timestamp is in the format 'YYYYmmddHHMMSS'
        timestamp = datetime.strptime(value, '%Y%m%d%H%M%S')
        return timestamp.strftime(format)
    except ValueError:
        return value  # Return the original value if there's an error

# Register the filter with the Jinja2 environment
app.jinja_env.filters['format_timestamp'] = format_timestamp

##### Formatting Functions for web frontend End #####

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

@app.route('/verify_pin', methods=['POST'])
def verify_pin_route():
    pin_provided = request.form.get('pin')
    if not pin_provided:
        return jsonify({'result': 'fail', 'message': 'No PIN provided'}), 400
    
    # Call the function from main.py to verify the PIN
    is_valid_pin = main.verify_pin(pin_provided)
    
    if is_valid_pin:
        return jsonify({'result': 'success', 'message': 'PIN is correct'}), 200
    else:
        return jsonify({'result': 'fail', 'message': 'Incorrect PIN'}), 403

