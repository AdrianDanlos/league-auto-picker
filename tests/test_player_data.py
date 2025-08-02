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


def test_player_data():
    """Test function to reset current rune page by setting it to null"""
    try:
        # Get LCU credentials
        port, token = get_lcu_credentials()
        base_url = f"https://127.0.0.1:{port}"
        auth = requests.auth.HTTPBasicAuth("riot", token)

        print(f"🔗 Connected to LCU API at {base_url}")

        # Get user data
        try:
            r = requests.get(
                f"{base_url}/lol-ranked/v1/current-ranked-stats", auth=auth, verify=False
            )
            print(f"🔍 stats: {r.json()}")

        except Exception as e:
            print(f"❌ Error getting stats: {e}")

    except RuntimeError as e:
        print(f"❌ {e}")
        print("Make sure League of Legends client is running.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    try:
        test_player_data()
    except KeyboardInterrupt:
        print("\n⏹️ Test stopped by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
