# flake8: noqa: E501
import requests
import time


def decline_incoming_swap_requests(base_url, auth):
    """
    Decline all incoming position swap requests.

    This function fetches all position swaps and declines any that are in "RECEIVED" state.
    It prioritizes the most recent swap request (highest ID) if multiple are received.

    Args:
        base_url (str): The base URL for the League Client API
        auth (tuple): Authentication credentials for the API requests

    Returns:
        bool: True if successfully declined a swap, False otherwise
    """
    while True:
        try:
            print("READY TO DECLINE")
            time.sleep(1)
            position_swaps_url = (
                f"{base_url}/lol-champ-select/v1/session/position-swaps"
            )
            position_swaps_res = requests.get(
                position_swaps_url, auth=auth, verify=False
            )
            print("position_swaps_res:", position_swaps_res)

            if position_swaps_res.status_code == 200:
                position_swaps = position_swaps_res.json()

                # Filter for state === "RECEIVED"
                received_swaps = [
                    swap for swap in position_swaps if swap.get("state") == "RECEIVED"
                ]

                if received_swaps:
                    # Pick the most recent one (highest id)
                    most_recent_swap = max(received_swaps, key=lambda x: x.get("id", 0))
                    swap_id = most_recent_swap.get("id")

                    if swap_id:
                        # Decline the swap
                        decline_url = f"{base_url}/lol-champ-select/v1/session/position-swaps/{swap_id}/decline"
                        decline_res = requests.post(
                            decline_url, auth=auth, verify=False
                        )

                        if decline_res.status_code == 200:
                            print(
                                f"[Pick Swap] Declined incoming position swap request (ID: {swap_id})"
                            )
                            return True
                        else:
                            print(
                                f"[Pick Swap] Failed to decline position swap: {decline_res.status_code}"
                            )
                    else:
                        print("[Pick Swap] No valid swap ID found in received swaps")
                # else:
                #     print("[Pick Swap] No received position swap requests to decline")
            else:
                print(
                    f"[Pick Swap] Failed to fetch position swaps: {position_swaps_res.status_code}"
                )
        except Exception as e:
            print(f"[Pick Swap] Exception while handling incoming swap requests: {e}")

        return False
