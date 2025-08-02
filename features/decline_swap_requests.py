import requests
import time

from features.send_discord_error_message import log_and_discord
from utils import get_session


def decline_incoming_swap_requests(base_url, auth):
    """
    Continuously monitor and decline all incoming swap requests during champion select.

    This function runs in an infinite loop, polling the League Client API every second
    to check for incoming swap requests. It handles three types of swaps:

    1. Position swaps: Requests to change lanes/roles (e.g., top to mid)
    2. Pick order swaps: Requests to change pick order in the draft
    3. Champion trades: Requests to trade champions between players

    The function prioritizes the most recent swap request (highest ID) when multiple
    requests are received simultaneously. It automatically declines any swap in the
    "RECEIVED" state to maintain the user's preferred position and picks.

    Args:
        base_url (str): The base URL for the League Client API (e.g., "https://127.0.0.1:2999")
        auth (tuple): Authentication credentials for the API requests, typically (username, password)
                     or a requests.auth.HTTPBasicAuth object

    Returns:
        None: This function runs indefinitely until interrupted or an error occurs

    Note:
        This function is designed to run in a separate thread or process during
        champion select to automatically handle incoming swap requests without
        user intervention.
    """
    while True:
        try:
            time.sleep(1)
            session = get_session(base_url, auth)
            if not session:
                return

            # Get all types of swaps from the session
            position_swaps = session.get("positionSwaps", [])
            pick_order_swaps = session.get("pickOrderSwaps", [])
            trades = session.get("trades", [])

            # Collect all received swaps from all types
            all_received_swaps = []

            # Process position swaps
            for swap in position_swaps:
                if swap.get("state") == "RECEIVED":
                    all_received_swaps.append(
                        {"id": swap.get("id"), "type": "position", "swap": swap}
                    )

            # Process pick order swaps
            for swap in pick_order_swaps:
                if swap.get("state") == "RECEIVED":
                    all_received_swaps.append(
                        {"id": swap.get("id"), "type": "pick_order", "swap": swap}
                    )

            # Process trades
            for trade in trades:
                if trade.get("state") == "RECEIVED":
                    all_received_swaps.append(
                        {"id": trade.get("id"), "type": "trade", "swap": trade}
                    )

            # Find the most recent swap (highest ID)
            if all_received_swaps:
                most_recent_swap = max(all_received_swaps, key=lambda x: x.get("id", 0))
                swap_id = most_recent_swap["id"]
                swap_type = most_recent_swap["type"]

                # Decline the swap based on its type
                if swap_type == "position":
                    decline_url = f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/decline"
                elif swap_type == "pick_order":
                    decline_url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/decline"
                elif swap_type == "trade":
                    decline_url = f"{base_url}/lol-champ-select/v1/session/trades/{swap_id}/decline"
                else:
                    log_and_discord(f"[Swap Decline] Unknown swap type: {swap_type}")
                    continue

                try:
                    decline_res = requests.post(decline_url, auth=auth, verify=False)
                except Exception as e:
                    log_and_discord(
                        f"[Swap Decline] Exception while trying to decline incoming swap request: {e}"
                    )

                if decline_res.status_code == 200 or decline_res.status_code == 204:
                    print(
                        f"[Swap Decline] Declined incoming {swap_type} swap request (ID: {swap_id})"
                    )
                else:
                    log_and_discord(
                        f"[Swap Decline] Failed to decline {swap_type} swap: {decline_res.status_code}"
                    )

            else:
                # No received requests
                continue
        except Exception as e:
            log_and_discord(
                f"[Swap Decline] Exception while handling incoming swap requests: {e}"
            )
            return
