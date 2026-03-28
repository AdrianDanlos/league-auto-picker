import requests
import time

from utils.logger import log_and_discord
from utils import get_auth, get_base_url, get_session, LeagueClientDisconnected


def accept_queue():
    """Polls the ready-check endpoint and accepts the match if found."""
    last_state = None
    while True:
        try:
            r = requests.get(
                f"{get_base_url()}/lol-matchmaking/v1/ready-check",
                auth=get_auth(),
                verify=False,
            )
            if r.status_code == 200:
                data = r.json()
                state = data.get("state")

                # Only log state changes to reduce spam
                if state != last_state:
                    if state == "InProgress":
                        print("🟢 Match found!")
                    elif state in ["Failed", "Cancelled", "Declined"]:
                        print(
                            f"🔄 Queue was {state.lower()}. Waiting for next queue..."
                        )
                    # In queue: state invalid
                    elif state in ["None", "Invalid"]:
                        print("🟢 Waiting for queue pop...")
                    else:
                        print(f"🔄 Queue state: {state}. Waiting...")
                    last_state = state

                if state == "InProgress":
                    accept = requests.post(
                        f"{get_base_url()}/lol-matchmaking/v1/ready-check/accept",
                        auth=get_auth(),
                        verify=False,
                    )

                    if accept.status_code != 204:
                        log_and_discord(
                            f"❌ Failed to accept queue: {accept.status_code} - {accept.text}"
                        )
                        break

                    print("✅ Queue accepted!")

                    # Wait for either champ select to start or queue to be cancelled
                    while True:
                        time.sleep(1)

                        # Check if champ select has started
                        if get_session():
                            print("🎮 Champion select started!")
                            return

                        # Re-check queue state
                        r = requests.get(
                            f"{get_base_url()}/lol-matchmaking/v1/ready-check",
                            auth=get_auth(),
                            verify=False,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            state = data.get("state")

                            # If queue was cancelled/declined, break out of waiting
                            if state in [
                                "None",
                                "Invalid",
                                "Failed",
                                "Cancelled",
                                "Declined",
                            ]:
                                print(
                                    f"🔄 Queue was {state.lower()}. Waiting for next queue..."
                                )
                                break

            time.sleep(1)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException,
            RuntimeError,
        ):
            # League client has disconnected - raise a generic exception
            raise LeagueClientDisconnected()
        except Exception as e:
            print(f"[Queue Accept Error]: {e}")
            time.sleep(5)
