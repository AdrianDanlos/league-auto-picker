# flake8: noqa: E501
import requests
import asyncio


def _attempt_swap_role(session, base_url, auth, config):
    """
    Checks for ongoing position swaps and attempts to swap roles if needed.

    Returns:
        bool: True if no ongoing swaps and role swap logic completed, False if ongoing swap detected
    """
    # Check if session is undefined or None
    if not session:
        print("[Role Swap] Session is undefined. Continuing script.")
        return True

    # Check for ongoing position swap requests
    try:
        ongoing_swap_url = f"{base_url}/lol-champ-select/v1/ongoing-position-swap"
        ongoing_res = requests.get(ongoing_swap_url, auth=auth, verify=False)
        if ongoing_res.status_code == 200 and ongoing_res.json():
            print("[Role Swap] Ongoing position swap detected. Skipping role swap.")
            return False
    except Exception as e:
        print(f"[Role Swap] Error checking ongoing swap: {e}")
        return True

    my_cell_id = session.get("localPlayerCellId")
    my_team = session.get("myTeam", [])

    # Find assigned role
    assigned_role = None
    for participant in my_team:
        if participant.get("cellId") == my_cell_id:
            assigned_role = participant.get("assignedPosition")
            break

    print("assigned_role:", assigned_role)
    if not assigned_role:
        print("[Role Swap] Could not determine assigned role.")
        return True

    preferred_role = config.get("preferred_role", "")
    if assigned_role == preferred_role:
        print(
            f"[Role Swap] Assigned role '{assigned_role}' is your preferred role. No swap needed."
        )
        return True

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
        return True

    # Find the correct swap ID from positionSwaps
    position_swaps = session.get("positionSwaps", [])
    target_cell_id = swap_target["cellId"]
    swap_id = None
    for swap in position_swaps:
        # The structure may vary, but typically there will be a cellId or similar field
        # Try to match the swap that involves the target cellId
        if (
            swap.get("cellId") == target_cell_id
            or swap.get("targetCellId") == target_cell_id
            or swap.get("receiverCellId") == target_cell_id
        ):
            swap_id = swap.get("id")
            break

    if not swap_id:
        print(f"[Role Swap] No position swap found for cellId {target_cell_id}.")
        return True

    # Request the swap using the swap ID
    request_swap_url = (
        f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/request"
    )
    try:
        request_res = requests.post(request_swap_url, auth=auth, verify=False)
        if request_res.status_code == 204:
            print(
                f"[Role Swap] Successfully requested swap with {preferred_role} (cellId {target_cell_id}, swapId {swap_id})"
            )
        else:
            print(
                f"[Role Swap] Role swap was declined: {request_res.status_code} {request_res.text}"
            )
    except Exception as e:
        print(f"[Role Swap] Exception during swap request: {e}")

    return True


async def swap_role(session, base_url, auth, config):
    """
    Async wrapper function that calls _attempt_swap_role in a loop every 1 second until it returns True.
    """
    print("🔄 Attempting role swap...")
    while True:
        result = _attempt_swap_role(session, base_url, auth, config)
        if result:
            print("[Role Swap] Role swap ended.")
            break
        print("[Role Swap] Waiting 1 second before next attempt...")
        await asyncio.sleep(1)
