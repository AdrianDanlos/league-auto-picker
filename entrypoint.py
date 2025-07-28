# flake8: noqa: E501
import time
import requests
import json
import urllib3
import psutil
import re
import asyncio

from accept_queue import accept_queue
from pick_and_ban import pick_and_ban
from swap_role import swap_role
from swap_pick_position import swap_pick_position
from send_message import send_champ_select_message
from utils import get_session

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


async def wait_for_champ_select(base_url, auth):
    session = None
    in_champ_select = False

    while True:
        # Try to accept queue - this will return if queue is cancelled
        accept_queue(base_url, auth)
        print("🟢 Waiting for Champ Select to start...")

        # Check if we entered champ select
        while True:
            session = get_session(base_url, auth)
            if session:
                if not in_champ_select:
                    print("🟢 Welcome to the Champ Select...")
                    in_champ_select = True
                # Stay in this loop until champ select ends
            else:
                if in_champ_select:
                    print(
                        "🔄 Champ select ended or was dodged. Waiting for queue pop again..."
                    )
                    in_champ_select = False
                    print("🟢 Waiting for queue pop...")
                    break  # Exit inner loop to try accepting next queue
            if in_champ_select and session:
                # Return session only when we have just entered champ select
                return session
            await asyncio.sleep(1)


async def main():
    port, token = get_lcu_credentials()
    base_url = f"https://127.0.0.1:{port}"
    auth = requests.auth.HTTPBasicAuth("riot", token)

    # Wait for a valid session (champ select)
    session = await wait_for_champ_select(base_url, auth)
    send_champ_select_message(session, base_url, auth)

    swap_role(session, base_url, auth, config)
    time.sleep(18)  # wait for role swap to complete
    print("[Role Swap] Role swap phase ended")
    pick_and_ban(base_url, auth, config)
    swap_pick_position(base_url, auth)    


if __name__ == "__main__":
    asyncio.run(main())
