import subprocess
import time
from telethon import TelegramClient, events, sync
from telethon.sync import TelegramClient
from datetime import datetime, timezone, timedelta
import requests
import json
import paramiko
from paramiko.ssh_exception import BadAuthenticationType, PartialAuthentication, AuthenticationException

count = 0

with open('config.json', 'r') as config:
    config = json.load(config)

def now():
    return datetime.now()

def status_checker():
    process_list = []
    command = f"ps -u {config['general']['process_user']} -o command | grep -e '{config['general']['process_to_watch']}'"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True)
    for line in process.stdout:
        if not 'bin' in line and not 'grep -e' in line:
            process_list.append(line)
    process_count = len(process_list)

    if process_count == 1:
        return "running"
    else:
        return "stopped"

def login_to_vps():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    vps_connect = client.connect(config['remote_vps']['vps_ip'], port=config['remote_vps']['vps_port'], username=config['remote_vps']['vps_user'], password=config['remote_vps']['vps_pass'])
    
    stdin, stdout, stderr = client.exec_command(f"ps -u {config['general']['process_user']} -o command | grep -e '{config['general']['process_to_watch']}'")

    process_list = []
    for line in stdout:
        if not 'bash' in line and not 'grep -e' in line:
            process_list.append(line)
    process_count = len(process_list)

    if process_count == 1:
        return "running"
    else:
        return "stopped"
    
def send_to_telegram(message):
    bot = TelegramClient(config['telegram']['tg_bot_name'], config['telegram']['tg_api_id'], config['telegram']['tg_api_hash'] ).start(bot_token=config['telegram']['tg_bot_token'])
    bot.start()
    bot.send_message(config['telegram']['tg_receiving_user'], f"{message}")
    bot.disconnect()

def send_to_discord(message):
    data = {"content": message}
    response = requests.post(config['discord']['d_webhook_url'], json=data)

if __name__ == '__main__':
    while True:
        if config['remote_vps']['enabled'] == True:
            status = login_to_vps()
        else:
            status = status_checker()
            
        if status == "stopped" and count == 0:
            message = config['general']['message']
            print(f"{now()}: {message}")
            if config['telegram']['enabled'] == True:
                send_to_telegram(message)
            if config['discord']['enabled'] == True:
                send_to_discord(message)
            count = 1
        elif status == "running":
            count = 0

        time.sleep(120)
