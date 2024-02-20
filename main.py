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
from datetime import datetime

print = functools.partial(print, flush=True) # for debugging, print messages show up in docker logs

## User Config Start

database_path = 'database.ini'

if not os.path.isfile(database_path):
    # Create default config if database.ini does not exist
    default_settings = configparser.ConfigParser()
    default_settings['Settings'] = {
        'Option1': 'False',
        'Option2': 'True',
        'Option3': 'False',
    }

    with open(database_path, 'w') as database_file:
        default_settings.write(database_file)

database = configparser.ConfigParser()
database.read(database_path)

## User Config End

def get_config():
    return conf.trackme

def get_usage(user, computer, ssh):
    # to do - maybe check if user is in timekpr first? (/usr/bin/timekpra --userlist)
    global timekpra_userinfo_output

    timekpra_userinfo_output = str(ssh.run(
            conf.ssh_timekpra_bin + ' --userinfo ' + user,
            hide=True
        ))

        # Save to database.ini
    save_to_ini(user, computer, timekpra_userinfo_output)

    database = configparser.ConfigParser()
    database.read('database.ini')
    section_name = f'{user}_{computer}'
    
    # Search if section exists
    if database.has_section(section_name):
        # Extract values
        timestamp = database.get(section_name, 'TIMESTAMP', fallback="Not found")
        time_left = database.getint(section_name, 'TIME_LEFT_DAY', fallback=0)
        time_spent = database.getint(section_name, 'TIME_SPENT_DAY', fallback=0)
        week_spent = database.getint(section_name, 'TIME_SPENT_WEEK', fallback=0)
        week_limit = database.getint(section_name, 'LIMIT_PER_WEEK', fallback=0)
        week_left = week_limit - week_spent
        
        # Gib die Werte als Dictionary zurück
        return {
            'timestamp': timestamp,
            'time_left': time_left, 
            'time_spent': time_spent,
            'week_left': week_left,
            'week_spent': week_spent,
            'result': 'success'
        }

def save_to_ini(user, computer, timekpra_userinfo_output):
    database = configparser.ConfigParser()
    database.read('database.ini')

    section_name = f'{user}_{computer}'
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
    global connection
    # todo handle SSH keys instead of forcing it to be passsword only
    connect_kwargs = {
        'allow_agent': False,
        'look_for_keys': False,
        "password": conf.ssh_password
    }
    try:
        connection = Connection(
            host=computer,
            user=conf.ssh_user,
            connect_kwargs=connect_kwargs
        )
    except AuthenticationException as e:
        print(f"Wrong credentials for user '{conf.ssh_user}' on host '{computer}'. "
              f"Check `ssh_user` and `ssh_password` credentials in conf.py.")
        raise e # handle exception in function that called this one
    except NoValidConnectionsError as e:
        print(f"Cannot connect to SSH server on host '{computer}'. "
              f"Check address in conf.py or try again later.")
        raise e # handle exception in function that called this one
    except Exception as e:
        print(f"Error logging in as user '{conf.ssh_user}' on host '{computer}', check conf.py. \n\n\t" + str(e))
        raise e # handle exception in function that called this one
    finally:
        return connection

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