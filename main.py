# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import conf, re
import configparser
import json
import json
import os
import functools # debug
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import NoValidConnectionsError
from datetime import datetime, timedelta

print = functools.partial(print, flush=True) # for debugging, print messages show up in docker logs

## User Config Start

default_user_settings = {
    'Option1': 'False',
    'Option2': 'True',
    'Option3': 'False',
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
database['DEFAULT'] = default_usage

# Check if the database.ini file exists
if not os.path.isfile('database.ini'):
    # Create the database.ini with default_user_settings if it does not exist
    database['Settings'] = default_user_settings
    with open('database.ini', 'w') as database_file:
        database.write(database_file)
else:
    # If database.ini exists, load the existing settings
    database.read('database.ini')
    # Check if the 'Settings' section exists
    if not database.has_section('Settings'):
        # Add the 'Settings' section and fill it with default_user_settings
        database['Settings'] = default_user_settings
    # Write the updated settings back to the database.ini
    with open('database.ini', 'w') as database_file:
        database.write(database_file)

## User Config End

def get_config():
    return conf.trackme

def get_usage(user, computer):
    database = configparser.ConfigParser()
    database.read('database.ini')
    section_name = f'{computer}_{user}'
    
    # Check if the section exists
    if not database.has_section(section_name):
        # If the section does not exist, inform the user and use default values
        error_message = f"Section {section_name} not found in database.ini; using default values."
        section_name = 'DEFAULT'  # Set to DEFAULT so it pulls the default values
    
    # Extract values using the DEFAULT section as fallback
    timestamp = database.get(section_name, 'TIMESTAMP', fallback='Never')
    time_left = database.getint(section_name, 'TIME_LEFT_DAY', fallback=0)
    time_spent = database.getint(section_name, 'TIME_SPENT_DAY', fallback=0)
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
    result = {
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
        result['error'] = error_message

    return result

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
            # Handle lines without ": "
            print(f"{__file__} {__name__}: Skipping line without ': ': {line}")

    with open('database.ini', 'w') as database_file:
        database.write(database_file)
        print(f"{__file__} {__name__}: INI file successfully updated.")


def get_connection(computer):
    # global ssh ## thread problem if global ?!?
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

        # to do - maybe check if user is in timekpr first? (/usr/bin/timekpra --userlist)
        # global timekpra_userinfo_output ## thread problem if global ?!?

        # timekpra_userinfo_output = str(ssh.run(
        #         conf.ssh_timekpra_bin + ' --userinfo ' + user,
        #         hide=True
        #     ))

        # # Save to database.ini
        # save_to_ini(user, computer, timekpra_userinfo_output)

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
    finally:
        return ssh

def adjust_time(up_down_string, seconds, ssh, user):
    command = conf.ssh_timekpra_bin + ' --settimeleft ' + user + ' ' + up_down_string + ' ' + str(seconds)
    ssh.run(command)
    if up_down_string == '-':
        print(f"removed {str(seconds)} for user {user}")
    else:
        print(f"added {str(seconds)} for user {user}")
    # todo - return false if this fails
    return True


def increase_time(seconds, ssh, user):
    return adjust_time('+', seconds, ssh, user)


def decrease_time(seconds, ssh, user):
    return adjust_time('-', seconds, ssh, user)