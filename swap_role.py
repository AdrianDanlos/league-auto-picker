# flake8: noqa: E501
import pyautogui
import time
from utils import get_pick_order


def swap_role(session, config):
    """
    Attempts to swap roles if assigned role is not the preferred_role.
    Simulates two clicks on the teammate with a preferred role using swap_role['first_click'] and swap_role['second_click'].
    """
    my_cell_id = session.get("localPlayerCellId")
    my_team = session.get("myTeam", [])
    assigned_role = None
    for participant in my_team:
        if participant.get("cellId") == my_cell_id:
            assigned_role = participant.get("assignedPosition")
            break
    print("assigned_role:", assigned_role)
    if not assigned_role:
        print("[Role Swap] Could not determine assigned role.")
        return
    preferred_role = config.get("preferred_role", "")
    if assigned_role == preferred_role:
        print(
            f"[Role Swap] Assigned role '{assigned_role}' is your preferred role. "
            "No swap needed."
        )
        return
    # Find a teammate with the preferred role
    swap_target = None
    for participant in my_team:
        print("preferred_role", preferred_role)
        print("participant.get(assignedPosition):", participant.get("assignedPosition"))
        if (
            participant.get("cellId") != my_cell_id
            and participant.get("assignedPosition") == preferred_role
        ):
            swap_target = participant
            break
    if not swap_target:
        print("[Role Swap] No teammate found with a preferred role to swap.")
        return
    # Get pick order for both players
    target_pick_order = get_pick_order(session, swap_target["cellId"])
    if not target_pick_order:
        print("[Role Swap] Could not determine target's pick order.")
        return
    if not (1 <= target_pick_order <= 5):
        print(
            f"[Role Swap] Target pick order {target_pick_order} is not in 1-5 "
            "(your team). Skipping role swap."
        )
        return
    coord_key = f"position_{target_pick_order}"
    coordinates1 = config.get("swap_role", {}).get("first_click", {}).get(coord_key)
    coordinates2 = config.get("swap_role", {}).get("second_click", {}).get(coord_key)
    if not coordinates1 or not coordinates2:
        print(f"[Role Swap] No coordinates found for pick order {target_pick_order}.")
        return
    x1, y1 = coordinates1["x"], coordinates1["y"]
    x2, y2 = coordinates2["x"], coordinates2["y"]
    print(
        f"[Role Swap] Attempting to swap with {swap_target['assignedPosition']} "
        f"at pick order {target_pick_order} (first click at {x1},{y1}, "
        f"second click at {x2},{y2})"
    )
    try:
        pyautogui.click(x1, y1)
        time.sleep(0.2)  # Small delay between clicks
        pyautogui.click(x2, y2)
        print("[Role Swap] Two click actions performed.")
    except Exception as e:
        print(f"[Role Swap] Failed to perform clicks: {e}")
