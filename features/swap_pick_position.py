import requests
import time
from utils.logger import log_and_discord
from utils import get_auth, get_base_url, get_session


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


def swap_pick_position():
    """
    Automatically requests pick order swaps to move to the 5th pick position.

    # The whole swap feature is only for top and middle

    This function continuously attempts to swap pick positions until the user reaches
    the 5th pick position. It intelligently handles ongoing swaps and manages
    swap requests to ensure smooth operation.

    Returns:
        None: Function returns None in all cases (void function)

    Behavior:
        The function operates in a continuous loop with the following steps:

        1. Check if already in 5th position - if so, exit
        2. Wait for any ongoing pick order swap in the lobby to complete
        3. Re-fetch session data to get current pick orders
        4. Find valid swap targets (players below your pick order):
           - Skip players already attempted in this round
           - Skip 5th TOP unless you are 4th pick
           - Prioritize highest pick order targets first
        5. Request swap with the best available target
        6. Repeat steps 2-5 until no valid targets remain
        7. Reset and try again from the beginning (in case new targets become available)

    API Endpoints Used:
        - GET /lol-champ-select/v1/session (via get_session)
        - GET /lol-champ-select/v1/ongoing-pick-order-swap
        - POST /lol-champ-select/v1/session/pick-order-swaps/{id}/request

    Notes:
        - The function continues running until you reach 5th position or encounter an error
        - Implements timeout mechanisms for ongoing swaps (up to 15 seconds)
        - Tracks attempted swaps to avoid infinite loops
        - Handles session errors gracefully (e.g., when someone dodges)
        - Prioritizes targets with higher pick orders for more efficient swapping
    """
    # Check if session is undefined or None (Someone dodged)
    if not get_session():
        return

    while True:
        try:
            session = get_session()
            # Check if session is None (someone dodged)
            if session is None:
                print(
                    "[Pick Swap] Session is None - someone may have dodged or game just started. Exiting..."
                )
                return
        except Exception as e:
            log_and_discord(f"[Pick Swap] Failed to fetch session: {e}")
            break

        my_cell_id = session.get("localPlayerCellId")
        my_pick_order = get_pick_order(session, my_cell_id)
        if not my_pick_order:
            log_and_discord("[Pick Swap] Could not determine your pick order.")
            break

        # If already in 5th position, no need to swap
        if my_pick_order == 5:
            print("[Pick Swap] Already in 5th position, no need to swap.")
            break

        attempted_cell_ids = set()
        while True:
            # 1. Wait for any ongoing pick order swap to complete
            wait_count = 0
            while wait_count < 10:  # Wait up to 30 seconds
                try:
                    ongoing_swap_url = (
                        f"{get_base_url()}/lol-champ-select/v1/ongoing-pick-order-swap"
                    )
                    ongoing_res = requests.get(
                        ongoing_swap_url, auth=get_auth(), verify=False
                    )
                    if ongoing_res.status_code == 200:
                        ongoing_swap = ongoing_res.json()
                        if ongoing_swap:
                            print(
                                f"[Pick Swap] Waiting for ongoing pick order swap to complete... ({wait_count + 1}/10)"
                            )
                            time.sleep(3)
                            wait_count += 1
                            continue
                        else:
                            print("[Pick Swap] No ongoing swap detected, proceeding...")
                            break  # No ongoing swap, proceed
                    else:
                        break  # Assume no ongoing swap if endpoint fails {ongoing_res.status_code}
                except Exception as e:
                    print(f"[Pick Swap] Failed to check ongoing swap: {e}")
                    break  # Proceed anyway if we can't check

            if wait_count >= 10:
                print(
                    "[Pick Swap] Timed out waiting for ongoing swap, proceeding anyway..."
                )

            # 2. Re-fetch session and get your pick order
            try:
                session = get_session()
                # Check if session is None (someone dodged)
                if session is None:
                    print(
                        "[Pick Swap] Session is None after re-fetch - someone may have dodged or game just started. Exiting..."
                    )
                    return
            except Exception as e:
                print(f"[Pick Swap] Failed to fetch session: {e}")
                break

            my_cell_id = session.get("localPlayerCellId")
            my_team = session.get("myTeam", [])
            my_pick_order = get_pick_order(session, my_cell_id)
            if not my_pick_order:
                log_and_discord("[Pick Swap] Could not determine your pick order.")
                break

            # 3. Calculate list of valid targets (players below you, excluding 5th TOP and already attempted)
            pick_orders = {}
            for participant in my_team:
                cell_id = participant.get("cellId")
                assigned_position = participant.get("assignedPosition")
                # The whole swap feature is only for top and middle
                if assigned_position not in ["top", "middle"]:
                    return
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
            url = f"{get_base_url()}/lol-champ-select/v1/session/pick-order-swaps/{swap_id}/request"
            try:
                res = requests.post(url, auth=get_auth(), verify=False)
                if (
                    res.status_code == 200
                    and res.text
                    and "INVALID" not in res.text
                    and "DECLINED" not in res.text
                ):
                    pass
                else:
                    # If someone declines, further requests will end up here
                    attempted_cell_ids.add(cell_id)

                # Wait 5 seconds after each request to prevent spam
                time.sleep(5)
            except Exception as e:
                log_and_discord(
                    f"[Pick Swap] Exception during swap request for cellId {cell_id}: {e}"
                )
                attempted_cell_ids.add(cell_id)

            # 7. Continue to next iteration (which will recalculate everything)

        # After inner loop ends, continue to outer loop to reset and try again
        # Add a 5-second delay to prevent rapid re-execution when no valid targets are found
        time.sleep(5)
