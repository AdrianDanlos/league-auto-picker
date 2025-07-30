import requests


def get_session(base_url, auth):
    r = requests.get(f"{base_url}/lol-champ-select/v1/session", auth=auth, verify=False)
    return r.json() if r.status_code == 200 else None
