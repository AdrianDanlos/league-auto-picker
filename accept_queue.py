# flake8: noqa: E501
import requests
import time


def accept_queue(base_url, auth):
    """Polls the ready-check endpoint and accepts the match if found."""
    last_state = None
    while True:
        try:
            r = requests.get(
                f"{base_url}/lol-matchmaking/v1/ready-check", auth=auth, verify=False
            )
            if r.status_code == 200:
                data = r.json()
                state = data.get("state")

                # Only log state changes to reduce spam
                if state != last_state:
                    if state == "InProgress":
                        print("🟢 Match found! Accepting queue...")
                    elif state in ["Failed", "Cancelled", "Declined"]:
                        print(
                            f"🔄 Queue was {state.lower()}. Waiting for next queue..."
                        )
                        break
                    elif state in ["None", "Invalid"]:
                        print("🟢 Waiting for queue pop...")
                    else:
                        print(f"🔄 Queue state: {state}. Waiting...")
                    last_state = state

                if state == "InProgress":
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
