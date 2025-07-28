# flake8: noqa: E501

import requests
import time
from utils import get_session, get_pick_order


def swap_pick_position(base_url, auth):
    """
    Automatically requests pick order swaps to move to the 5th pick position.

    This function continuously attempts to swap pick positions until the user reaches
    the 5th pick position. It handles incoming swap requests intelligently and
    manages ongoing swaps to ensure smooth operation.

    Args:
        base_url (str): The base URL for the League Client API
        auth (tuple): Authentication credentials for the API requests

    Returns:
        None: Function returns None in all cases (void function)

    Behavior:
        The function operates in a continuous loop with the following steps:

        1. Check if already in 5th position - if so, exit
        2. Handle incoming pick order swap requests:
           - Accept requests from players below your pick order (moves you later)
           - Decline requests from players above your pick order (moves you earlier)
        3. Wait for any ongoing pick order swap in the lobby to complete
        4. Re-fetch session data to get current pick orders
        5. Find valid swap targets (players below your pick order):
           - Skip players already attempted in this round
           - Skip 5th TOP unless you are 4th pick
           - Prioritize highest pick order targets first
        6. Request swap with the best available target
        7. Repeat steps 2-6 until no valid targets remain
        8. Reset and try again from the beginning (in case new targets become available)

    API Endpoints Used:
        - GET /lol-champ-select/v1/session (via get_session)
        - GET /lol-champ-select/v1/ongoing-pick-order-swap
        - POST /lol-champ-select/v1/session/pick-order-swaps/{id}/request
        - POST /lol-champ-select/v1/session/pick-order-swaps/{id}/accept
        - POST /lol-champ-select/v1/session/pick-order-swaps/{id}/decline

    Notes:
        - The function continues running until you reach 5th position or encounter an error
        - Includes intelligent handling of incoming swap requests
        - Implements timeout mechanisms for ongoing swaps
        - Tracks attempted swaps to avoid infinite loops
    """
    # Check if session is undefined or None
    if not get_session(base_url, auth):
        print("[Role Swap] Session is undefined. Continuing script.")
        return

    while True:
        # Check if we're already in 5th position
        try:
            session = get_session(base_url, auth)
        except Exception as e:
            print(f"[Pick Swap] Failed to fetch session: {e}")
            break

        my_cell_id = session.get("localPlayerCellId")
        my_pick_order = get_pick_order(session, my_cell_id)
        if not my_pick_order:
            print("[Pick Swap] Could not determine your pick order.")
            break

        # If already in 5th position, no need to swap
        if my_pick_order == 5:
            print("[Pick Swap] Already in 5th position, no need to swap.")
            break

        attempted_cell_ids = set()
        while True:
            # 0. Handle any incoming pick order swap requests
            try:
                session = get_session(base_url, auth)
                my_cell_id = session.get("localPlayerCellId")
                my_pick_order = get_pick_order(session, my_cell_id)
                pick_order_swaps = session.get("pickOrderSwaps", [])

                for swap in pick_order_swaps:
                    # Check if this is an incoming swap request to us
                    if swap.get("id") == my_cell_id and not swap.get("completed", True):
                        # The requester is the other participant in this swap
                        requester_cell_id = None
                        for participant in session.get("myTeam", []):
                            participant_cell_id = participant.get("cellId")
                            if participant_cell_id != my_cell_id:
                                # Check if this participant has a swap request to us
                                for other_swap in pick_order_swaps:
                                    if (
                                        other_swap.get("id") == participant_cell_id
                                        and other_swap.get("completed") == False
                                    ):
                                        requester_cell_id = participant_cell_id
                                        break
                            if requester_cell_id:
                                break

                        if requester_cell_id:
                            requester_pick_order = get_pick_order(
                                session, requester_cell_id
                            )

                            # Find the swap id for the swap between us and the requester
                            swap_id = None
                            for s in pick_order_swaps:
                                # The swap should involve both our cell id and the requester
                                # Try to match either direction (id == my_cell_id or id == requester_cell_id)
                                if (
                                    s.get("id") == my_cell_id
                                    and s.get("cellId") == requester_cell_id
                                ) or (
                                    s.get("id") == requester_cell_id
                                    and s.get("cellId") == my_cell_id
                                ):
                                    swap_id = s.get("id")
                                    break
                            if not swap_id:
                                # Fallback: try to use the requester's cell id
                                swap_id = requester_cell_id

                            if requester_pick_order and my_pick_order:
                                if requester_pick_order < my_pick_order:
                                    # Request from someone above us - decline
                                    decline_url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/decline"
                                    decline_res = requests.post(
                                        decline_url, auth=auth, verify=False
                                    )
                                    if (
                                        decline_res.status_code == 200
                                        or decline_res.status_code == 204
                                    ):
                                        print(
                                            f"[Pick Swap] Declined incoming swap request from pick order {requester_pick_order} (above us)"
                                        )
                                    else:
                                        print(
                                            f"[Pick Swap] Failed to decline swap request: {decline_res.status_code}"
                                        )
                                elif requester_pick_order > my_pick_order:
                                    # Request from someone below us - accept
                                    accept_url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/accept"
                                    accept_res = requests.post(
                                        accept_url, auth=auth, verify=False
                                    )
                                    if (
                                        accept_res.status_code == 200
                                        or accept_res.status_code == 204
                                    ):
                                        print(
                                            f"[Pick Swap] Accepted incoming swap request from pick order {requester_pick_order} (below us)"
                                        )
                                    else:
                                        print(
                                            f"[Pick Swap] Failed to accept swap request: {accept_res.status_code}"
                                        )
            except Exception as e:
                print(f"[Pick Swap] Failed to handle incoming swap requests: {e}")

            # Small delay after handling incoming requests
            time.sleep(1)

            # 1. Wait for any ongoing pick order swap to complete
            wait_count = 0
            while wait_count < 30:  # Wait up to 60 seconds
                try:
                    ongoing_swap_url = (
                        f"{base_url}/lol-champ-select/v1/ongoing-pick-order-swap"
                    )
                    ongoing_res = requests.get(
                        ongoing_swap_url, auth=auth, verify=False
                    )
                    if ongoing_res.status_code == 200:
                        ongoing_swap = ongoing_res.json()
                        if ongoing_swap:
                            print(
                                f"[Pick Swap] Waiting for ongoing pick order swap to complete... ({wait_count + 1}/30)"
                            )
                            time.sleep(2)
                            wait_count += 1
                            continue
                        else:
                            print("[Pick Swap] No ongoing swap detected, proceeding...")
                            break  # No ongoing swap, proceed
                    else:
                        print(
                            f"[Pick Swap] Ongoing swap check failed: {ongoing_res.status_code}"
                        )
                        break  # Assume no ongoing swap if endpoint fails
                except Exception as e:
                    print(f"[Pick Swap] Failed to check ongoing swap: {e}")
                    break  # Proceed anyway if we can't check

            if wait_count >= 30:
                print(
                    "[Pick Swap] Timed out waiting for ongoing swap, proceeding anyway..."
                )

            # 2. Re-fetch session and get your pick order
            try:
                session = get_session(base_url, auth)
            except Exception as e:
                print(f"[Pick Swap] Failed to fetch session: {e}")
                break
            my_cell_id = session.get("localPlayerCellId")
            my_team = session.get("myTeam", [])
            my_pick_order = get_pick_order(session, my_cell_id)
            if not my_pick_order:
                print("[Pick Swap] Could not determine your pick order.")
                break

            # 3. Calculate list of valid targets (players below you, excluding 5th TOP and already attempted)
            pick_orders = {}
            for participant in my_team:
                cell_id = participant.get("cellId")
                assigned_position = participant.get("assignedPosition")
                pick_order = get_pick_order(session, cell_id)
                if (
                    pick_order
                    and pick_order > my_pick_order
                    and cell_id not in attempted_cell_ids
                ):
                    # Exclude 5th TOP unless I am 4th pick
                    if not (
                        pick_order == 5
                        and assigned_position
                        and assigned_position.upper() == "TOP"
                        and my_pick_order != 4
                    ):
                        pick_orders[cell_id] = (pick_order, assigned_position)

            # 4. If no valid targets, break out of inner loop to reset and try again
            if not pick_orders:
                break

            # 5. Pick the best target (highest pick order)
            cell_id, (pick_order, assigned_position) = sorted(
                pick_orders.items(), key=lambda x: -x[1][0]
            )[0]

            # 6. Find the correct swap ID from pickOrderSwaps
            pick_order_swaps = session.get("pickOrderSwaps", [])
            swap_id = None

            # Find the swap that corresponds to our target cell ID
            for swap in pick_order_swaps:
                if swap.get("cellId") == cell_id:
                    swap_id = swap.get("id")
                    break

            if not swap_id:
                attempted_cell_ids.add(cell_id)
                continue

            # 7. Make the swap request
            url = f"{base_url}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/request"
            try:
                res = requests.post(url, auth=auth, verify=False)
                print("🟢 res.text:", res.text)
                if res.status_code == 200 and res.text and "INVALID" not in res.text:
                    print(
                        f"[Pick Swap] Successfully requested swap with {assigned_position} at pick order {pick_order} (cellId {cell_id}, swapId {swap_id})"
                    )
                    # Wait a bit after successful request to let it process
                    time.sleep(3)
                else:
                    print(
                        f"[Pick Swap] Failed to request swap: {res.status_code} {res.text}"
                    )
                    attempted_cell_ids.add(cell_id)
            except Exception as e:
                print(
                    f"[Pick Swap] Exception during swap request for cellId {cell_id}: {e}"
                )
                attempted_cell_ids.add(cell_id)

            # 7. Continue to next iteration (which will recalculate everything)

        # After inner loop ends, continue to outer loop to reset and try again
