import requests
import time

from features.send_discord_error_message import log_and_discord
from lcu_connection import get_session


def get_pick_order(session, cell_id):
    """
    Returns the pick order (1-based index) for the given cell_id based on your team's pick actions.
    """
    actions = session.get("actions", [])
    my_team_cell_ids = {p["cellId"] for p in session.get("myTeam", [])}
    pick_order = 1
    for action_group in actions:
        for action in action_group:
            if action["type"] == "pick" and action["actorCellId"] in my_team_cell_ids:
                if action["actorCellId"] == cell_id:
                    return pick_order
                pick_order += 1
    return None


def handle_incoming_swap_requests(base_url, auth):
    """
    Continuously monitor and accept incoming swap requests from players below us during champion select.

    This function runs in an infinite loop, polling the League Client API every second
    to check for incoming swap requests. It handles three types of swaps:

    1. Position swaps: Requests to change lanes/roles (e.g., top to mid)
    2. Pick order swaps: Requests to change pick order in the draft
    3. Champion trades: Requests to trade champions between players

    The function prioritizes the most recent swap request (highest ID) when multiple
    requests are received simultaneously. It automatically accepts swaps from players
    with a higher pick order number (lower pick position) than us, and declines
    swaps from players with a lower pick order number (higher pick position) than us.

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
            time.sleep(5)  # Wait 5 seconds between requests to prevent spam
            session = get_session(base_url, auth)
            if not session:
                return

            # Get our pick order
            my_cell_id = session.get("localPlayerCellId")
            my_pick_order = get_pick_order(session, my_cell_id)
            if not my_pick_order:
                log_and_discord("[Swap Handler] Could not determine your pick order.")
                continue

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
                swap_data = most_recent_swap["swap"]

                # Determine the requester's cell ID and pick order
                requester_cell_id = None
                if swap_type == "position":
                    requester_cell_id = swap_data.get("requesterId")
                elif swap_type == "pick_order":
                    requester_cell_id = swap_data.get("requesterId")
                elif swap_type == "trade":
                    requester_cell_id = swap_data.get("requesterId")

                if not requester_cell_id:
                    log_and_discord(
                        f"[Swap Handler] Could not determine requester for {swap_type} swap"
                    )
                    continue

                requester_pick_order = get_pick_order(session, requester_cell_id)
                if not requester_pick_order:
                    log_and_discord(
                        f"[Swap Handler] Could not determine requester's pick order for {swap_type} swap"
                    )
                    continue

                # Accept if requester has higher pick order number (lower pick position)
                # Decline if requester has lower pick order number (higher pick position)
                should_accept = requester_pick_order > my_pick_order

                if should_accept:
                    # Accept the swap
                    if swap_type == "position":
                        accept_url = f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/accept"
                    elif swap_type == "pick_order":
                        accept_url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/accept"
                    elif swap_type == "trade":
                        accept_url = f"{base_url}/lol-champ-select/v1/session/trades/{swap_id}/accept"
                    else:
                        log_and_discord(
                            f"[Swap Handler] Unknown swap type: {swap_type}"
                        )
                        continue

                    try:
                        accept_res = requests.post(accept_url, auth=auth, verify=False)
                    except Exception as e:
                        log_and_discord(
                            f"[Swap Handler] Exception while trying to accept incoming swap request: {e}"
                        )
                        continue

                    if accept_res.status_code == 200 or accept_res.status_code == 204:
                        print(
                            f"[Swap Handler] Accepted incoming {swap_type} swap request from player {requester_pick_order} (ID: {swap_id})"
                        )
                    else:
                        log_and_discord(
                            f"[Swap Handler] Failed to accept {swap_type} swap: {accept_res.status_code}"
                        )
                else:
                    # Decline the swap
                    if swap_type == "position":
                        decline_url = f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/decline"
                    elif swap_type == "pick_order":
                        decline_url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/decline"
                    elif swap_type == "trade":
                        decline_url = f"{base_url}/lol-champ-select/v1/session/trades/{swap_id}/decline"
                    else:
                        log_and_discord(
                            f"[Swap Handler] Unknown swap type: {swap_type}"
                        )
                        continue

                    try:
                        decline_res = requests.post(
                            decline_url, auth=auth, verify=False
                        )
                    except Exception as e:
                        log_and_discord(
                            f"[Swap Handler] Exception while trying to decline incoming swap request: {e}"
                        )
                        continue

                    if decline_res.status_code == 200 or decline_res.status_code == 204:
                        print(
                            f"[Swap Handler] Declined incoming {swap_type} swap request from player {requester_pick_order} (ID: {swap_id})"
                        )
                    else:
                        log_and_discord(
                            f"[Swap Handler] Failed to decline {swap_type} swap: {decline_res.status_code}"
                        )

            else:
                # No received requests
                continue
        except Exception as e:
            log_and_discord(
                f"[Swap Handler] Exception while handling incoming swap requests: {e}"
            )
            return
