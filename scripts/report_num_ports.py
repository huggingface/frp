# WIP

import requests
import os
from apscheduler.schedulers.blocking import BlockingScheduler
import time

max_num_live_interfaces = 0
total_num_live_interfaces = 0
interface_ip_set = set()

def daily_analytics():
    global max_num_live_interfaces
    global total_num_live_interfaces
    global interface_ip_set
    url = 'https://slack.com/api/chat.postMessage'
    headers = {"Authorization": "Bearer xoxp-59424140306-2786565709460-2891580133511-b94712c2bd741bd7d84e3f98682beb02"}

    daily1 = {'channel': 'C02S0FL2D8R', 'unfurl_links': 'true', 'as_user':
        'true', 'text': 'Max Number of Shared Interfaces (past 24 hrs): {}'
                        '\n'
                        'Total Number of Shared Interfaces (past 24 hrs): {'
                        '}' .format(str(int(
                            max_num_live_interfaces)), str(int(
                            total_num_live_interfaces)))
            }

    dailyPosts = [daily1]

    for dailyPost in dailyPosts:
        requests.post(url, data=dailyPost, headers=headers)

    max_num_live_interfaces = 0
    total_num_live_interfaces = 0
    interface_ip_set = set()


def get_total_num_live_interfaces():
    global total_num_live_interfaces
    global interface_ip_set
    sudo_password = ''
    command = 'lsof -PiTCP -sTCP:LISTEN'
    open_ports = os.popen(
        'echo %s|sudo -S %s' % (sudo_password, command)).read()
    ip_split = open_ports.split("IPv6")
    for i in ip_split:
        if 'paramiko' in i:
            interface_ip_set.add(i[1:9])
    total_num_live_interfaces = len(interface_ip_set)

def get_max_live_interfaces():
    global max_num_live_interfaces
    sudo_password = ''
    command = 'lsof -PiTCP -sTCP:LISTEN'
    open_ports = os.popen(
        'echo %s|sudo -S %s' % (sudo_password, command)).read()
    num_live_interfaces = 0
    x = open_ports.split("IPv6")

    for i in x:
        if 'paramiko' in i:
            num_live_interfaces = num_live_interfaces + 1

    num_live_interfaces = num_live_interfaces
    if num_live_interfaces > max_num_live_interfaces:
        max_num_live_interfaces = num_live_interfaces


get_total_num_live_interfaces()
get_max_live_interfaces()
daily_analytics()
time.sleep(10)

scheduler = BlockingScheduler()
scheduler.add_job(get_total_num_live_interfaces, 'interval', minutes=1)
scheduler.add_job(get_max_live_interfaces, 'interval', minutes=1)
scheduler.add_job(daily_analytics, 'interval', hours=24)
print("Analytics Job Starting...")
scheduler.start()