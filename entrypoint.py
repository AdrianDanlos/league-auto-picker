# flake8: noqa: E501
import requests
import time
import json
import urllib3
import psutil
import re

from send_message import send_champ_select_message

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Load config ===
with open("config.json") as f:
    config = json.load(f)


def get_lcu_credentials():
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


def get_session(base_url, auth):
    r = requests.get(f"{base_url}/lol-champ-select/v1/session", auth=auth, verify=False)
    return r.json() if r.status_code == 200 else None


def wait_for_champ_select(base_url, auth):
    session = None
    while not session:
        print("🟢 Waiting for queue pop...")
        accept_queue(base_url, auth)
        print("🟢 Waiting for champ select...")
        time.sleep(10)  # wait for everyone to accept the queue
        session = get_session(base_url, auth)
        if session:
            print("🟢 Welcome to the Champ Select...")
            time.sleep(4)  # wait for the champ select to load
        else:
            print("🔄 No session found. Retrying queue pop...")
    return session


if __name__ == "__main__":
    import pygetwindow as gw
    from accept_queue import accept_queue
    from pick_and_ban import pick_and_ban
    from swap_role import swap_role
    from swap_pick_position import swap_pick_position

    port, token = get_lcu_credentials()
    base_url = f"https://127.0.0.1:{port}"
    auth = requests.auth.HTTPBasicAuth("riot", token)

    # Wait for a valid session (champ select)
    session = wait_for_champ_select(base_url, auth)
    send_champ_select_message(session, base_url, auth)

    # Only done once
    swap_role(session, config)
    time.sleep(10)  # wait until the role swap ends

    # Main loop: only runs after a valid session is acquired
    while True:
        try:
            if session:
                # Refresh session to get the latest state of the champ select
                session = get_session(base_url, auth)
                swap_pick_position(session, config)
                pick_and_ban(session, base_url, auth, config)
            else:
                session = wait_for_champ_select(base_url, auth)

            time.sleep(13)
        except Exception as e:
            print("[Error]", e)
            time.sleep(5)
