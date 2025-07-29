# flake8: noqa: E501
import requests


def swap_role(session, base_url, auth, config):
    """
    Checks for ongoing position swaps and attempts to swap roles if needed.

    This function analyzes the current champion select session to determine if the user
    is assigned to their preferred role. If not, it attempts to find a teammate with
    the preferred role and requests a position swap.

    The function performs the following steps:
    1. Checks for ongoing position swaps to avoid conflicts
    2. Determines the user's currently assigned role
    3. Compares assigned role with preferred role from config
    4. Searches for teammates with the preferred role
    5. Requests position swap if suitable teammate is found

    API Endpoints Used:
        - GET /lol-champ-select/v1/ongoing-position-swap
        - POST /lol-champ-select/v1/session/position-swaps/{swapId}/request

    Args:
        session (dict): The League Client API session object containing:
            - localPlayerCellId (int): The cell ID of the local player
            - myTeam (list): List of team participants with cellId and assignedPosition
            - positionSwaps (list): Available position swap options with id, cellId, etc.
        base_url (str): The base URL for the League Client API (e.g., "https://127.0.0.1:2999")
        auth (tuple): Authentication credentials for the API requests (username, password)
        config (dict): Configuration dictionary containing:
            - preferred_role (str): The user's preferred role (e.g., "TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY")

    Returns:
        None: Function returns None in all cases (void function)

    Raises:
        No exceptions are raised; all errors are handled internally with logging

    Behavior:
        - Checks for ongoing position swaps and skips if one is detected
        - Compares assigned role with preferred role from config
        - Searches for teammates with the preferred role
        - Requests position swap if suitable teammate is found
        - Handles API errors gracefully with appropriate logging
        - Recursively calls itself if no swap ID is found (retry mechanism)
    """
    # Check if session is undefined or None (Someone dodged)
    if not session:
        return

    # Check for ongoing position swap requests
    try:
        ongoing_swap_url = f"{base_url}/lol-champ-select/v1/ongoing-position-swap"
        ongoing_res = requests.get(ongoing_swap_url, auth=auth, verify=False)
        if ongoing_res.status_code == 200 and ongoing_res.json():
            print("[Role Swap] Ongoing position swap detected. Skipping role swap.")
            return
    except Exception as e:
        print(f"[Role Swap] Error checking ongoing swap: {e}")
        return

    my_cell_id = session.get("localPlayerCellId")
    my_team = session.get("myTeam", [])

    # Find assigned role
    assigned_role = None
    for participant in my_team:
        if participant.get("cellId") == my_cell_id:
            assigned_role = participant.get("assignedPosition")
            break

    if not assigned_role:
        print("[Role Swap] Could not determine assigned role.")
        return

    preferred_role = config.get("preferred_role", "")
    if assigned_role == preferred_role:
        print(
            f"[Role Swap] Assigned role '{assigned_role}' is your preferred role. No swap needed."
        )
        return

    # Find a teammate with the preferred role
    swap_target = None
    for participant in my_team:
        if (
            participant.get("cellId") != my_cell_id
            and participant.get("assignedPosition") == preferred_role
        ):
            swap_target = participant
            break

    if not swap_target:
        print("[Role Swap] No teammate found with a preferred role to swap.")
        return

    # Find the correct swap ID from positionSwaps
    position_swaps = session.get("positionSwaps", [])
    target_cell_id = swap_target["cellId"]
    swap_id = None

    for swap in position_swaps:
        if (
            swap.get("cellId") == target_cell_id
            or swap.get("targetCellId") == target_cell_id
            or swap.get("receiverCellId") == target_cell_id
        ):
            swap_id = swap.get("id")
            break

    if not swap_id:
        print(f"[Role Swap] No position swap found for cellId {target_cell_id}.")
        print(f"[Role Swap] Available swaps: {position_swaps}")
        print("🟢 calling again swap_role(session, base_url, auth, config)")
        swap_role(session, base_url, auth, config)
        return

    # Request the swap using the swap ID
    request_swap_url = (
        f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/request"
    )
    try:
        request_res = requests.post(request_swap_url, auth=auth, verify=False)
        if request_res.status_code == 204 or request_res.status_code == 200:
            print(
                f"[Role Swap] Requested role swap with {preferred_role} (cellId {target_cell_id}, swapId {swap_id})"
            )
        else:
            print(
                f"[Role Swap] Role swap error: {request_res.status_code} {request_res.text}"
            )
    except Exception as e:
        print(f"[Role Swap] Exception during swap request: {e}")

    return
