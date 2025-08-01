import requests


def select_default_runes(base_url, auth):
    try:
        response = requests.post(
            f"{base_url}/lol-perks/v1/rune-recommender-auto-select",
            auth=auth,
            verify=False,
        )

        if response.status_code == 200 or response.status_code == 204:
            print("✅ Successfully set current rune page to reccommended one")
        else:
            print(
                f"❌ Failed to set current rune page to reccomended one (Status: {response.status_code})"
            )
            if response.text:
                print(f"📝 Error response: {response.text}")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")


# Get current rune page
# try:
#     current_page_response = requests.get(
#         f"{base_url}/lol-perks/v1/currentpage", auth=auth, verify=False
#     )
#     if current_page_response.status_code == 200:
#         current_page = current_page_response.json()
#         print(f"📄 Current rune page: {current_page}")
#     else:
#         print(
#             f"❌ Failed to get current rune page: {current_page_response.status_code}"
#         )
# except Exception as e:
#     print(f"❌ Error getting current rune page: {e}")
