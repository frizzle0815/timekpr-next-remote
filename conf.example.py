trackme = {
    '10.220.249.232': ["user", "display_name"], # first value is user on device you want to control, second value is alias for display
}
ssh_user = 'timekpr-next-remote'
ssh_password = 'timekpr-next-remote'
ssh_timekpra_bin = '/usr/bin/timekpra'
ssh_key = './id_timekpr'
pin_code = '123456' # prevents unauthorized time changes; leave empty to disable


# Examples
# 
# trackme = {
#     '10.220.249.232': [["mrjones", "jones_on_device1"],["antonia", "antonia_on_device1"]], 
# }

# trackme = {
#     '10.220.249.232': ["mrjones", "jones_device1"], 
#     '10.220.249.547': ["mrjones", "jones_device2"], 
# }