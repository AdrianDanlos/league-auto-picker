from utils.lcu_connection import get_auth, get_base_url, get_session
from utils.session_utils import get_summoner_name
from utils.logger import log_and_discord


def send_discord_error_message(error):
    try:
        session = get_session(get_base_url(), get_auth())
        summoner_name = get_summoner_name(session)
        log_and_discord(error, summoner_name)

    except Exception:
        pass
        # print(f"❌ Unexpected error sending error message to discord: {e}")


def log_and_discord_wrapper(error):
    """
    Wrapper function to maintain backward compatibility.
    This function now delegates to the logger module.

    Args:
        error (str): The error message to print and send to Discord
    """
    log_and_discord(error)
