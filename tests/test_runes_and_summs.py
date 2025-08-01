import requests
import urllib3
import psutil
import re

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_lcu_credentials():
    """Get League Client credentials from running process"""
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found.")


def test_rune_page_reset():
    """Test function to reset current rune page by setting it to null"""
    try:
        # Get LCU credentials
        port, token = get_lcu_credentials()
        base_url = f"https://127.0.0.1:{port}"
        auth = requests.auth.HTTPBasicAuth("riot", token)

        print(f"🔗 Connected to LCU API at {base_url}")

        # Get current rune page
        try:
            current_page_response = requests.get(
                f"{base_url}/lol-perks/v1/currentpage", auth=auth, verify=False
            )
            if current_page_response.status_code == 200:
                current_page = current_page_response.json()
                print(f"📄 Current rune page: {current_page}")
            else:
                print(
                    f"❌ Failed to get current rune page: {current_page_response.status_code}"
                )
        except Exception as e:
            print(f"❌ Error getting current rune page: {e}")

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

        try:
            response = requests.patch(
                f"{base_url}/lol-champ-select/v1/session/my-selection",
                auth=auth,
                json={"spell1Id": 4, "spell2Id": 12},
                verify=False,
            )

            if response.status_code == 200 or response.status_code == 204:
                print("✅ Successfully set the summoner spells")
            else:
                print(
                    f"❌ Failed to set the summoner spells (Status: {response.status_code})"
                )
                if response.text:
                    print(f"📝 Error response: {response.text}")

        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    except RuntimeError as e:
        print(f"❌ {e}")
        print("Make sure League of Legends client is running.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    print("🧪 Starting rune page reset test...")
    print("This test will continuously attempt to set the current rune page to 0")
    print("Press Ctrl+C to stop the test\n")

    try:
        test_rune_page_reset()
    except KeyboardInterrupt:
        print("\n⏹️ Test stopped by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
