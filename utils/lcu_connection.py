import requests
import psutil
import re

from .exceptions import LeagueClientDisconnected


def get_lcu_credentials():
    for proc in psutil.process_iter(["cmdline"]):
        if proc.info["cmdline"] and "LeagueClientUx.exe" in proc.info["cmdline"][0]:
            cmdline = " ".join(proc.info["cmdline"])
            port = re.search(r"--app-port=(\d+)", cmdline).group(1)
            token = re.search(r"--remoting-auth-token=([\w-]+)", cmdline).group(1)
            return port, token
    raise RuntimeError("League client not found. Please start League of Legends first.")


# Initialize these as None, will be set when needed
_port = None
_token = None
_base_url = None
_auth = None


def _ensure_credentials():
    """Ensure credentials are loaded, fetch them if needed"""
    global _port, _token, _base_url, _auth
    if _port is None or _token is None:
        _port, _token = get_lcu_credentials()
        _base_url = f"https://127.0.0.1:{_port}"
        _auth = requests.auth.HTTPBasicAuth("riot", _token)


def get_base_url():
    """Get the base URL for LCU API calls"""
    _ensure_credentials()
    return _base_url


def get_auth():
    """Get the authentication for LCU API calls"""
    _ensure_credentials()
    return _auth


def get_session():
    """Get the current champ select session"""
    try:
        r = requests.get(
            f"{get_base_url()}/lol-champ-select/v1/session",
            auth=get_auth(),
            verify=False,
        )
        return r.json() if r.status_code == 200 else None
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.RequestException,
        RuntimeError,
    ):
        # League client has disconnected - raise a generic exception
        raise LeagueClientDisconnected()
    except Exception as e:
        print(f"⚠️  Error connecting to League client: {e}")
        return None
