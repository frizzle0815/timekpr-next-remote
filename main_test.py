database = configparser.ConfigParser()
database.read('database.ini')

ssh_user = database['ssh']['ssh_user']
ssh_password = database['ssh']['ssh_password']
ssh_timekpra_bin = database['ssh']['ssh_timekpra_bin']
ssh_key = database['ssh']['ssh_key']


def get_timekpr_userinfo(computer, user):
    global ssh
    # todo handle SSH keys instead of forcing it to be passsword only
    connect_kwargs = {
        'allow_agent': False,
        'look_for_keys': False,
        'password': ssh_password,
        'timeout': 3
    }
    try:
        ssh = Connection(
            host=computer,
            user=ssh_user,
            connect_kwargs=connect_kwargs
        )

        # to do - maybe check if user is in timekpr first? (/usr/bin/timekpra --userlist)
        global timekpra_userinfo_output

        timekpra_userinfo_output = str(ssh.run(
                ssh_timekpra_bin + ' --userinfo ' + user,
                hide=True
            ))

        # Save to database.ini
        save_to_ini(user, computer, timekpra_userinfo_output)

    except AuthenticationException as e:
        print(f"Wrong credentials for user '{ssh_user}' on host '{computer}'. "
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
        print(f"Error logging in as user '{ssh_user}' on host '{computer}', check conf.py. \n\n\t" + str(e))
        raise e # handle exception in function that called this one
    finally:
        return ssh

