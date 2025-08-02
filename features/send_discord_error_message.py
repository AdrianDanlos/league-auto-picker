import requests

from lcu_connection import auth, base_url, get_session
from utils import get_summoner_name

webhook_url = "https://discord.com/api/webhooks/1401132002693873674/2QGQjoLaeESr4QhK6qMt3ortI5ChkZIIfp3L3uznlgBDI96C1IBAmVWkklVc8LeyoJ-v"


def send_discord_error_message(error):
    try:
        session = get_session(base_url, auth)
        summoner_name = get_summoner_name(session)
        data = {"content": f"{summoner_name}: {error}"}

        response = requests.post(webhook_url, json=data)

        if response.status_code == 204:
            print("✅ Discord error message sent")
        else:
            print(f"❌ Error sending discord error message: {response.status_code}")

    except Exception as e:
        print(f"❌ Unexpected error sending error message to discord: {e}")


def log_and_discord(error):
    """
    Unified function to print a message and send it to Discord as an error message.

    Args:
        message (str): The message to print and send to Discord
    """
    print(error)
    send_discord_error_message(error)
