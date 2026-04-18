import time
import requests
from utils import shared_state, LeagueClientDisconnected, get_auth, get_base_url
from features.discord_message import get_game_data
from features.post_game.post_game_utils import sanitize_last_game_data, get_rank_changes
from features.discord_message import (
    get_gameflow_phase,
    send_discord_post_game_message,
)

# gameflow-phase can flip through EndOfGame in under 3s; polling faster + eog-stats
# catches post-game reliably. Only trust eog-stats when phase is still post-game-ish,
# so a stale payload in Lobby does not fire a duplicate message.
_EOG_PHASES_ALLOW_STATS_ENDPOINT = frozenset(
    {
        "EndOfGame",
        "WaitingForStats",
        "PreEndOfGame",
    }
)


def _eog_stats_block_available():
    try:
        r = requests.get(
            f"{get_base_url()}/lol-end-of-game/v1/eog-stats-block",
            auth=get_auth(),
            verify=False,
        )
        if r.status_code != 200:
            return False
        data = r.json()
        if not isinstance(data, dict):
            return False
        return bool(data.get("teams"))
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.RequestException,
        RuntimeError,
    ):
        raise LeagueClientDisconnected()
    except Exception:
        return False


def start_end_of_game_actions():
    message_sent = False
    last_sent_game_id = None
    post_game_phases = set(_EOG_PHASES_ALLOW_STATS_ENDPOINT) | {"Lobby"}
    while True:
        try:
            gameflow_phase = get_gameflow_phase()
            # New game / champ select: allow another post-game message after this match.
            if gameflow_phase in ("ChampSelect", "InProgress"):
                message_sent = False

            eog_ready = _eog_stats_block_available()
            should_attempt_post_game = gameflow_phase in post_game_phases and (
                gameflow_phase == "EndOfGame" or eog_ready
            )

            if (
                should_attempt_post_game
                and not message_sent
                and shared_state.current_queue_type is not None
            ):
                sanitized_last_game = sanitize_last_game_data()
                current_game_id = (
                    sanitized_last_game.get("game_id")
                    if isinstance(sanitized_last_game, dict)
                    else None
                )

                # Avoid duplicate messages for the same game.
                if current_game_id and current_game_id == last_sent_game_id:
                    message_sent = True
                else:
                    game_data = get_game_data()
                    sent = send_discord_post_game_message(
                        sanitized_last_game,
                        get_rank_changes(),
                        game_data.get("summoner_name"),
                    )
                    if sent:
                        print("🟡 END OF GAME gameflow_phase", gameflow_phase)
                        message_sent = True
                        if current_game_id:
                            last_sent_game_id = current_game_id
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException,
            RuntimeError,
            LeagueClientDisconnected,
        ):
            # Set a flag to indicate the client disconnected (don't print here, main thread handles it)
            shared_state.client_disconnected = True
            break
        except Exception as e:
            print(f"❌ Error in end game actions: {e}")
            # Continue running for other types of errors
        time.sleep(1)
