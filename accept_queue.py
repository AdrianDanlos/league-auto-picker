# flake8: noqa: E501
import requests
import time


def accept_queue(base_url, auth):
    """Polls the ready-check endpoint and accepts the match if found."""
    while True:
        try:
            r = requests.get(
                f"{base_url}/lol-matchmaking/v1/ready-check", auth=auth, verify=False
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("state") == "InProgress":
                    print("🟢 Match found! Accepting queue...")
                    accept = requests.post(
                        f"{base_url}/lol-matchmaking/v1/ready-check/accept",
                        auth=auth,
                        verify=False,
                    )
                    if accept.status_code == 204:
                        print("✅ Queue accepted!")
                        break
                    else:
                        print(f"❌ Failed to accept queue: {accept.status_code}")
            time.sleep(1)
        except Exception as e:
            print("[Queue Accept Error]", e)
            time.sleep(5)
