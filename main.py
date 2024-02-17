# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import conf, re
import configparser
import json
import os
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import NoValidConnectionsError
from datetime import datetime


## User Config Start

config_path = 'user_config.ini'

if not os.path.isfile(config_path):
    # Create default config if user_config.ini does not exist
    default_config = configparser.ConfigParser()
    default_config['Settings'] = {
        'Option1': 'False',
        'Option2': 'True',
        'Option3': 'False',
    }

    with open(config_path, 'w') as config_file:
        default_config.write(config_file)

config = configparser.ConfigParser()
config.read(config_path)

## User Config End

def get_config():
    return conf.trackme


def get_usage(user, computer, ssh):
    # to do - maybe check if user is in timekpr first? (/usr/bin/timekpra --userlist)
    global timekpra_userinfo_output
    fail_json = {'time_left': 0, 'time_spent': 0, 'result': 'fail'}
    try:
        timekpra_userinfo_output = str(ssh.run(
                conf.ssh_timekpra_bin + ' --userinfo ' + user,
                hide=True
            ))
    except NoValidConnectionsError as e:
        print(f"Cannot connect to SSH server on host '{computer}'. "
              f"Check address in conf.py or try again later.")
        return fail_json
    except AuthenticationException as e:
        print(f"Wrong credentials for user '{conf.ssh_user}' on host '{computer}'. "
              f"Check `ssh_user` and `ssh_password` credentials in conf.py.")
        return fail_json
    except Exception as e:
        quit(f"Error logging in as user '{conf.ssh_user}' on host '{computer}', check conf.py. \n\n\t" + str(e))
        return fail_json

    search = r"(TIME_LEFT_DAY: )([0-9]+)"
    time_left = re.search(search, timekpra_userinfo_output)
    search = r"(TIME_SPENT_DAY: )([0-9]+)"
    time_spent = re.search(search, timekpra_userinfo_output)

    # todo - better handle "else" when we can't find time remaining
    if not time_left or not time_left.group(2):
        print(f"Error getting time left, setting to 0. ssh call result: " + str(timekpra_userinfo_output))
        return fail_json
    else:
        time_left = str(time_left.group(2))
        time_spent = str(time_spent.group(2))
        print(f"Time left for {user} at {computer}: {time_left}")

        # Save to user_config.ini
        save_to_ini(user, computer, timekpra_userinfo_output)

        return {'time_left': time_left, 'time_spent': time_spent, 'result': 'success'}

def save_to_ini(user, computer, timekpra_userinfo_output):
    config = configparser.ConfigParser()
    config.read('user_config.ini')

    section_name = f'{user}_{computer}'
    if not config.has_section(section_name):
        config.add_section(section_name)
        print(f"Section {section_name} has been added.")

    # Add current Timestamp
    timestamp_key = 'TIMESTAMP'
    timestamp_value = str(datetime.now())
    config.set(section_name, timestamp_key, timestamp_value)

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
            config.set(section_name, key, value)
        else:
            # Handle lines without ": " (optional)
            print(f"Skipping line without ': ': {line}")

    with open('user_config.ini', 'w') as config_file:
        config.write(config_file)
        print("INI file successfully updated.")


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
        quit(f"Wrong credentials for user '{conf.ssh_user}' on host '{computer}'. "
              f"Check `ssh_user` and `ssh_password` credentials in conf.py.")
    except Exception as e:
        quit(f"Error logging in as user '{conf.ssh_user}' on host '{computer}', check conf.py. \n\n\t" + str(e))
    finally:
        return connection

def adjust_time(up_down_string, seconds, ssh, user):
    command = conf.ssh_timekpra_bin + ' --settimeleft ' + user + ' ' + up_down_string + ' ' + str(seconds)
    ssh.run(command)
    if up_down_string == '-':
        print(f"added {str(seconds)} for user {user}")
    else:
        print(f"removed {str(seconds)} for user {user}")
    # todo - return false if this fails
    return True


def increase_time(seconds, ssh, user):
    return adjust_time('+', seconds, ssh, user)


def decrease_time(seconds, ssh, user):
    return adjust_time('-', seconds, ssh, user)



