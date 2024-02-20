# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import conf, re
import configparser
import json
import os
import functools # debug
from fabric import Connection
from paramiko.ssh_exception import AuthenticationException
from paramiko.ssh_exception import NoValidConnectionsError
from datetime import datetime

print = functools.partial(print, flush=True) # for debugging, print messages show up in docker logs

## User Config Start

config_path = 'database.ini'
global config

if not os.path.isfile(config_path):
    # Create default config if database.ini does not exist
    default_config = configparser.ConfigParser()
    default_config['Settings'] = {
        'option1': 'False',
        'option2': 'True',
        'option3': 'False',
    }

    with open(config_path, 'w') as config_file:
        default_config.write(config_file)

config = configparser.ConfigParser()
config.read(config_path)

## User Config End

def get_database():
    config = configparser.ConfigParser()
    config.read('database.ini')
    return config

def get_config():
    return conf.trackme


def get_usage(user, computer):
    config = configparser.ConfigParser()
    config.read('database.ini')
    section_name = f'{user}_{computer}'
    
    # Search if section exists
    if config.has_section(section_name):
      # Extract values
      timestamp = config.get(section_name, 'TIMESTAMP', fallback="Not found")
      time_left = config.getint(section_name, 'TIME_LEFT_DAY', fallback=0)
      time_spent = config.getint(section_name, 'TIME_SPENT_DAY', fallback=0)
      week_spent = config.getint(section_name, 'TIME_SPENT_WEEK', fallback=0)
      week_limit = config.getint(section_name, 'LIMIT_PER_WEEK', fallback=0)
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

#    search = r"(TIME_LEFT_DAY: )([0-9]+)"
#    time_left = re.search(search, timekpra_userinfo_output)
#    search = r"(TIME_SPENT_DAY: )([0-9]+)"
#    time_spent = re.search(search, timekpra_userinfo_output)
#
#    # todo - better handle "else" when we can't find time remaining
#    if not time_left or not time_left.group(2):
#        print(f"Error getting time left, setting to 0. ssh call result: " + str(timekpra_userinfo_output))
#        return fail_json
#    else:
#        time_left = str(time_left.group(2))
#        time_spent = str(time_spent.group(2))
#        print(f"Time left for {user} at {computer}: {time_left}")
#

#
#        return {'time_left': time_left, 'time_spent': time_spent, 'result': 'success'}

def save_to_ini(user, computer, timekpra_userinfo_output):
    config = configparser.ConfigParser()
    config.read('database.ini')

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
            # Handle lines without ": "
            print(f"{__file__} {__name__}: Skipping line without ': ': {line}")

    with open('database.ini', 'w') as config_file:
        config.write(config_file)
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



