# flake8: noqa: E501

# Add pyautogui for click simulation
import pyautogui
import time
from utils import get_pick_order


def swap_pick_position(session, config):
    """
    Checks the current player's pick order and asks to swap with every player below them,
    starting from the 5th position (unless it's top), then 4th, 3rd, and 2nd.
    Only asks players below the current pick order, and skips asking top if they're in 5th position.
    Simulates the swap request clicks using the config's swap_pick_position coordinates.
    """
    my_cell_id = session.get("localPlayerCellId")
    my_team = session.get("myTeam", [])
    actions = session.get("actions", [])

    # Get my pick order
    my_pick_order = get_pick_order(session, my_cell_id)
    if not my_pick_order:
        print("[Pick Swap] Could not determine your pick order.")
        return

    # Build a map of cellId to (pick_order, assignedPosition)
    pick_orders = {}
    for participant in my_team:
        cell_id = participant.get("cellId")
        assigned_position = participant.get("assignedPosition")
        pick_order = get_pick_order(session, cell_id)
        if pick_order:
            pick_orders[cell_id] = (pick_order, assigned_position)

    # Sort teammates by pick order descending (5th to 2nd)
    sorted_teammates = sorted(
        [item for item in pick_orders.items() if item[1][0] > my_pick_order],
        key=lambda x: -x[1][0],
    )

    for cell_id, (pick_order, assigned_position) in sorted_teammates:
        # Only ask if below me
        if pick_order <= my_pick_order:
            continue
        # If 5th position and assigned_position is TOP, skip
        if pick_order == 5 and assigned_position and assigned_position.upper() == "TOP":
            print(f"[Pick Swap] Skipping TOP in 5th position (cellId {cell_id}).")
            continue
        coord_key = f"position_{pick_order}"
        coordinates1 = (
            config.get("swap_pick_position", {}).get("first_click", {}).get(coord_key)
        )
        coordinates2 = (
            config.get("swap_pick_position", {}).get("second_click", {}).get(coord_key)
        )
        if not coordinates1 or not coordinates2:
            print(f"[Pick Swap] No coordinates found for pick order {pick_order}.")
            continue
        x1, y1 = coordinates1["x"], coordinates1["y"]
        x2, y2 = coordinates2["x"], coordinates2["y"]

        try:
            pyautogui.click(x1, y1)
            time.sleep(0.2)
            pyautogui.click(x2, y2)
            print(
                f"[Pick Swap] Asking {assigned_position} at pick order {pick_order} (cellId {cell_id}) to swap."
            )
        except Exception as e:
            print(f"[Pick Swap] Failed to perform clicks for cellId {cell_id}: {e}")
