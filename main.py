# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import conf  # Used for accessing configuration variables like `conf.trackme`, `conf.ssh_password`, etc.
import configparser  # Used for reading and writing the 'database.ini' file
import os  # Used to check if the 'database.ini' file exists with os.path.isfile
import re  # If you are using regular expressions in your code
import functools  # Used to override the print function for flushing output
from fabric import Connection  # Used to establish SSH connections
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError  # Used to handle SSH connection exceptions
from datetime import datetime, timedelta  # Used to handle timestamps and time calculations
import threading  # Used to create and manage threading events and threads
import time  # Used to create sleep delays in threads
import socket  # Used to handle socket.timeout exception which can occur during SSH connection

print = functools.partial(print, flush=True) # for debugging, print messages show up in docker logs

# Create a threading event that can be set or cleared to control the loop
background_service_event = threading.Event()

##### Initializing Start #####

default_user_settings = {
    'background_service': 'false',
    'option2': 'true',
    'option3': 'false',
}

default_usage = {
    'TIMESTAMP': '-1',
    'LIMIT_PER_WEEK': '0',
    'LIMIT_PER_MONTH': '0',
    'TIME_SPENT_BALANCE': '0',
    'TIME_SPENT_DAY': '0',
    'TIME_SPENT_WEEK': '0',
    'TIME_SPENT_MONTH': '0',
    'TIME_LEFT_DAY': '0',
    'PLAYTIME_LEFT_DAY': '0',
    'PLAYTIME_SPENT_DAY': '0',
    'ACTUAL_TIME_SPENT_SESSION': '0',
    'ACTUAL_TIME_INACTIVE_SESSION': '0',
    'ACTUAL_TIME_SPENT_BALANCE': '0',
    'ACTUAL_TIME_SPENT_DAY': '0',
    'ACTUAL_TIME_LEFT_DAY': '0',
    'ACTUAL_TIME_LEFT_CONTINUOUS': '0',
    'ACTUAL_PLAYTIME_LEFT_DAY': '0',
    'ACTUAL_ACTIVE_PLAYTIME_ACTIVITY_COUNT': '0',
}

# Initialize the configparser
database = configparser.ConfigParser()

# Set default values for all usage sections
database['DEFAULT_USAGE'] = default_usage

# Check if the database.ini file exists
if not os.path.isfile('database.ini'):
    # Create the database.ini with default_user_settings if it does not exist
    database['settings'] = default_user_settings
    with open('database.ini', 'w') as database_file:
        database.write(database_file)
else:
    # If database.ini exists, load the existing settings
    database.read('database.ini')
    # Check if the 'settings' section exists
    if not database.has_section('settings'):
        # Add the 'settings' section and fill it with default_user_settings
        database['settings'] = default_user_settings
    # Write the updated settings back to the database.ini
    with open('database.ini', 'w') as database_file:
        database.write(database_file)

##### Initializing End #####

##### Background Service Start #####

def check_connection():
    while background_service_event.is_set():
        config = configparser.ConfigParser()
        config.read('database.ini')
        
        trackme_config = get_config()
        
        for computer, userArrays in trackme_config.items():
            for users in userArrays:  # More than one user on one device
                user = users[0]  # Use only first value in array = use user and ignore display_name
                ssh = None
                try:
                    ssh = get_connection(computer)
                    if ssh:
                        # First, update user info and ensure the operation is complete to avoid race conditions => data conflict!
                        update_userinfo(ssh, computer, user)
                        # Then, process pending time changes
                        process_pending_time_changes(computer, ssh)
                except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
                    print(f"No connection to {computer}: {e}")
                finally:
                    if ssh:
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

##### Background Service End #####

##### Update Timekpr Userinfo Start ##### 

def get_config():
    return conf.trackme

def get_connection(computer):

    # todo handle SSH keys instead of forcing it to be passsword only
    connect_kwargs = {
        'allow_agent': False,
        'look_for_keys': False,
        'password': conf.ssh_password,
        'timeout': 3
    }
    try:
        ssh = Connection(
            host=computer,
            user=conf.ssh_user,
            connect_kwargs=connect_kwargs
        )
        return ssh

    except AuthenticationException as e:
        print(f"Wrong credentials for user '{conf.ssh_user}' on host '{computer}'. "
              f"Check `ssh_user` and `ssh_password` credentials in conf.py.")
        raise e # handle exception in function that called this one
    except NoValidConnectionsError as e:
        print(f"Cannot connect to SSH server on host '{computer}'. "
              f"Check address in conf.py or try again later.")
        raise e # handle exception in function that called this one
    except socket.timeout:
        print(f"Connection timed out on '{computer}'.")
        raise e    
    except Exception as e:
        print(f"Error logging in as user '{conf.ssh_user}' on host '{computer}', check conf.py. \n\n\t" + str(e))
        raise e # handle exception in function that called this one

def update_userinfo(ssh, computer, user):
    try:
        timekpra_userinfo_output = str(ssh.run(
            conf.ssh_timekpra_bin + ' --userinfo ' + user,
            hide=True
        ))
        save_to_ini(user, computer, timekpra_userinfo_output)
    except (AuthenticationException, NoValidConnectionsError, socket.timeout, Exception) as e:
        error_message = str(e)
        print(f"Failed to update userinfo for {user} on {computer}: {error_message}")
        return {'result': "fail", 'message': error_message}
    else:
        print(f"Userinfo updated successfully for {user} on {computer}")
        return {'result': "success", 'message': "Userinfo updated successfully"}


def save_to_ini(user, computer, timekpra_userinfo_output):
    database = configparser.ConfigParser()
    database.read('database.ini')

    section_name = f'{computer}_{user}'
    if not database.has_section(section_name):
        database.add_section(section_name)
        print(f"Section {section_name} has been added.")

    # Add current Timestamp
    timestamp_key = 'TIMESTAMP'
    timestamp_value = str(datetime.now())
    database.set(section_name, timestamp_key, timestamp_value)

    # Split the timekpra_userinfo_output string into lines and process each line
    for line in timekpra_userinfo_output.split('\n'):
        # Skip empty lines
        if not line.strip():
            continue

        # Split each line into key and value using ": "
        line_parts = line.split(': ', 1)
        if len(line_parts) == 2:
            key, value = map(str.strip, line_parts)
            # Set the key-value pair in the INI file
            database.set(section_name, key, value)
        else:
            # If a line without ": " is found, do nothing and continue
            pass

    with open('database.ini', 'w') as database_file:
        database.write(database_file)
        print(f"{__file__} {__name__}: SUCCESS: usage for {user} on {computer} updated.")

##### Update Timekpr Userinfo End ##### 

##### Update Web Frontend Start ##### 

def get_usage(user, computer):
    database = configparser.ConfigParser()
    database.read('database.ini')
    section_name = f'{computer}_{user}'
    
    # Check if the section exists
    if not database.has_section(section_name):
        # If the section does not exist, inform the user and use default values
        error_message = f"Section {section_name} not found in database.ini; using default values."
        section_name = 'DEFAULT_USAGE'  # Set to DEFAULT so it pulls the default values
    
    # Extract values using the DEFAULT section as fallback
    timestamp = database.get(section_name, 'TIMESTAMP', fallback='Never')
    time_left = database.getint(section_name, 'ACTUAL_TIME_LEFT_DAY', fallback=0)
    time_spent = database.getint(section_name, 'ACTUAL_TIME_SPENT_DAY', fallback=0)
    week_spent = database.getint(section_name, 'TIME_SPENT_WEEK', fallback=0)
    week_limit = database.getint(section_name, 'LIMIT_PER_WEEK', fallback=0)
    week_left = week_limit - week_spent
    
    # Calculate last_seen
    last_seen = ""
    if timestamp == "-1":
        last_seen = "Never"
    else:
        # Calculate last_seen based on the timestamp
        try:
            timestamp_dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
            now = datetime.now()
            time_since = now - timestamp_dt
            seconds_ago = time_since.total_seconds()

            if seconds_ago < 60:
                last_seen = f"{int(seconds_ago)} seconds ago"
            elif seconds_ago < 3600:
                minutes = seconds_ago // 60
                last_seen = f"{int(minutes)} minutes ago"
            elif seconds_ago < 86400:
                hours = seconds_ago // 3600
                last_seen = f"{int(hours)} hours ago"
            else:
                days = seconds_ago // 86400
                last_seen = f"{int(days)} days ago"
        except ValueError:
            # Handle the case where the timestamp format is incorrect
            last_seen = "Timestamp format error"

    # Prepare the result dictionary
    usage = {
        'timestamp': timestamp,
        'last_seen': last_seen,
        'time_left': time_left, 
        'time_spent': time_spent,
        'week_left': week_left,
        'week_spent': week_spent,
        'result': 'success'
    }

    # Add the error message if the section was not found
    if 'error_message' in locals():
        usage['error'] = error_message

    return usage

##### Update Web Frontend End ##### 

##### Time Change Queue Start #####

def queue_time_change(user, computer, action, seconds, status='pending'):
    database = configparser.ConfigParser()
    database.read('database.ini')

    try:
        # Check if a section for Time Changes exists, if not create it
        if 'time_changes' not in database.sections():
            database.add_section('time_changes')

        # Check for existing pending entries for this computer-user combination
        for key, value in database.items('time_changes'):
            if key.startswith(f"{computer}_{user}_") and value.endswith("pending"):
                # Change the status of the existing pending entry to 'cancelled'
                database.set('time_changes', key, value.replace("pending", "cancelled"))

        # Create a unique key for the new change request
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        change_key = f"{computer}_{user}_{timestamp}"

        # Add the new change request to the section with status 'pending'
        database.set('time_changes', change_key, f"{action},{seconds},{status}")

        # Clean up non-pending entries to keep only the last 5 for this user
        non_pending_changes = [key for key, value in database.items('time_changes')
                               if key.startswith(f"{computer}_{user}_") and not value.endswith("pending")]
        # Sort non-pending changes by timestamp (assuming the timestamp is at the end of the key)
        non_pending_changes.sort(key=lambda x: x.split('_')[-1], reverse=True)
        # Remove entries beyond the 5th one
        for old_change in non_pending_changes[5:]:
            database.remove_option('time_changes', old_change)

        # Write the changes back to database.ini file once
        with open('database.ini', 'w') as configfile:
            database.write(configfile)

        print(f"Time change queued for {user} on {computer}: {action} {seconds} seconds")
    except Exception as e:
        print(f"An error occurred while updating the database.ini file: {e}")
        # Handle the error, possibly restoring from a backup or retrying the operation

def process_pending_time_changes(computer, ssh):
    database = configparser.ConfigParser()
    database.read('database.ini')

    if 'time_changes' in database.sections():
        for key, value in database.items('time_changes'):
            # Extract computer from the key and check if it matches the given computer
            key_computer, user, _ = key.split('_')  # Assuming the key format is "computer_user_timestamp"
            if key_computer == computer and value.endswith("pending"):
                up_down_string, seconds, status = value.split(',')
                success = False

                # Directly call adjust_time with the appropriate sign based on the action
                if up_down_string == 'add':
                    success = adjust_time('+', seconds, ssh, user)
                elif up_down_string == 'remove':
                    success = adjust_time('-', seconds, ssh, user)

                # If success, update the status in the database
                if success:
                    new_status = "success"
                    database.set('time_changes', key, f"{up_down_string},{seconds},{new_status}")
                else:
                    # Print the message indicating that the attempt failed and will be retried next time
                    print(f"Attempt to adjust time for user {user} failed. Retrying next time...")

        # Write the changes back to database.ini file if any changes were made
        with open('database.ini', 'w') as configfile:
            database.write(configfile)

def adjust_time(up_down_string, seconds, ssh, user):
    command = f"{conf.ssh_timekpra_bin} --settimeleft {user} {up_down_string} {seconds}"
    try:
        ssh.run(command)
        print(f"{'Removed' if up_down_string == '-' else 'Added'} {seconds} seconds for user {user}")
        return True
    except Exception as e:
        print(f"Failed to adjust time for user {user}: {e}")
        return False

##### Time Change Queue End #####

def validate_request(computer, user):
    if computer not in conf.trackme:
        return {'result': "fail", "message": "computer not in config"}
    # Check if any sublist in the list for the computer contains the user
    if not any(user in userArray for userArray in conf.trackme[computer]):
        return {'result': "fail", "message": "user not in computer in config"}
    else:
        return {'result': "success", "message": "valid user and computer"}