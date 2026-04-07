import time
import json
import urllib3
import threading
import sys
import utils.lcu_connection as lcu

from features.post_game.end_of_game_actions import start_end_of_game_actions
from features.discord_message import (
    create_discord_message,
    get_game_data,
    send_discord_pre_game_message,
)
from features.accept_queue import accept_queue
from features.pick_and_ban import pick_and_ban
from features.decline_swap_requests import decline_incoming_swap_requests
from features.swap_role import swap_role
from features.swap_pick_position import swap_pick_position
from features.send_chat_message import schedule_champ_select_message
from features.post_game.post_game_utils import save_pre_game_lp
from features.session_lane_prompt import (
    consume_session_champ_select_message,
    consume_session_preferred_role,
)
from utils import (
    get_base_url,
    get_auth,
    get_current_champion_id_lcu,
    get_session,
    get_queueType,
    get_final_local_champion_name,
    fetch_champion_names,
    LeagueClientDisconnected,
)
from utils.logger import logger
from utils import shared_state
from utils.config_validation import validate_config

# Disable warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# === Load config ===
try:
    with open("config.json") as f:
        config = json.load(f)
except FileNotFoundError:
    print("❌ config.json not found. Please ensure the configuration file exists.")
    sys.exit(1)
except json.JSONDecodeError:
    print("❌ Invalid JSON in config.json. Please check the file format.")
    sys.exit(1)

validation_errors, validation_warnings = validate_config(config)
if validation_errors:
    print("❌ Invalid config.json. Please fix the following issues:")
    for err in validation_errors:
        print(f"   - {err}")
    sys.exit(1)
if validation_warnings:
    print("⚠️ config.json warnings:")
    for warning in validation_warnings:
        print(f"   - {warning}")


def check_league_client():
    """Check if League client is running and accessible"""
    try:
        get_base_url()
        get_auth()
        return True
    except RuntimeError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ Error connecting to League client: {e}")
        return False


def check_league_client_silent():
    """Check if League client is running and accessible (no error messages)"""
    try:
        get_base_url()
        get_auth()
        return True
    except Exception:
        return False


def start_end_of_game_thread():
    """Start the end of game monitoring thread"""
    end_of_game_thread = threading.Thread(target=start_end_of_game_actions)
    end_of_game_thread.daemon = True
    end_of_game_thread.start()
    return end_of_game_thread


def wait_for_champ_select():
    """Synchronous version - blocks until champ select starts"""
    while True:
        accept_queue()
        # After accept_queue returns, get the champ select session
        # Wait 3 seconds before getting the session to let everything load
        time.sleep(3)
        session = get_session()
        return session


def main():
    # Start logging system
    logger.start_logging()

    print("🎮 League Auto Picker starting...")
    print("📋 Make sure you have:")
    print("   • League of Legends running")
    print("   • config.json properly configured")
    print()

    # Check if League client is accessible
    if not check_league_client():
        print("\n🔄 Waiting for League client to start...")
        print(
            "   Please start League of Legends and press Enter to retry, or Ctrl+C to exit."
        )

        while True:
            try:
                input()
                if check_league_client():
                    break
                print(
                    "🔄 League client still not accessible. Please ensure it's running and try again."
                )
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                sys.exit(0)

    print("✅ Connected to League client successfully!")
    shared_state.config_preferred_role = config.get("preferred_role")

    try:
        # Start end of game actions in a single long-lived thread
        start_end_of_game_thread()

        while True:
            try:
                # Check if League client disconnected from background thread
                if shared_state.client_disconnected:

                    # Reset credentials cache
                    lcu._port = None
                    lcu._token = None
                    lcu._base_url = None
                    lcu._auth = None

                    # Reset shared state
                    shared_state.client_disconnected = False
                    shared_state.current_queue_type = None

                    # Wait for League client to be available again instead of restarting
                    print("🔄 Waiting for League client to restart...")
                    while True:
                        try:
                            time.sleep(5)  # Wait 5 seconds between checks
                            if check_league_client_silent():
                                print("✅ League client reconnected!")
                                shared_state.config_preferred_role = config.get(
                                    "preferred_role"
                                )
                                break
                        except KeyboardInterrupt:
                            print("\n👋 Shutting down gracefully...")
                            return

                    continue

                # Wait for a valid session (champ select)
                # This blocks until queue is accepted
                session = wait_for_champ_select()

                # Save LP before game starts
                shared_state.current_queue_type = get_queueType(session)
                if not shared_state.current_queue_type:
                    # Skip current iteration of loop. The queue is not supported.
                    continue

                save_pre_game_lp(shared_state.current_queue_type)

                session_preferred_role = consume_session_preferred_role(
                    config.get("preferred_role"), wait_for_selection_seconds=8
                )
                session_chat_override = consume_session_champ_select_message()
                schedule_champ_select_message(
                    session, message_override=session_chat_override
                )
                swap_role(
                    session,
                    config,
                    preferred_role_override=session_preferred_role,
                )

                # Run concurrently in separate threads
                pick_ban_thread = threading.Thread(
                    target=pick_and_ban, args=(config, session_preferred_role)
                )
                swap_position_thread = threading.Thread(target=swap_pick_position)

                handle_incoming_swap_requests_thread = threading.Thread(
                    target=decline_incoming_swap_requests
                )

                pick_ban_thread.daemon = True
                swap_position_thread.daemon = True
                handle_incoming_swap_requests_thread.daemon = True

                pick_ban_thread.start()
                swap_position_thread.start()
                handle_incoming_swap_requests_thread.start()

                # Wait for threads to complete (they will run until champ select ends)
                pick_ban_thread.join()
                swap_position_thread.join()
                handle_incoming_swap_requests_thread.join()

                session = get_session()
                if session:
                    final_name = get_final_local_champion_name(session)
                    if final_name:
                        create_discord_message(final_name, session)
                else:
                    fallback_id = get_current_champion_id_lcu()
                    if fallback_id:
                        fname = fetch_champion_names().get(fallback_id)
                        if fname:
                            shared_state.game_data["picked_champion"] = fname

                game_data = get_game_data()
                send_discord_pre_game_message(game_data)

                print("🟡 Champ select ended!")

                # Small delay before checking for next queue
                time.sleep(2)

            except KeyboardInterrupt:
                print("\n👋 Shutting down gracefully...")
                break
            except LeagueClientDisconnected:
                print("🔄 League client disconnected")
                shared_state.client_disconnected = True
                continue
            except Exception as e:
                print(f"❌ Error during game session: {e}")
                print("🔄 Restarting and waiting for next queue...")
                time.sleep(5)  # Wait a bit before retrying
                continue
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error during game session: {e}")
    finally:
        # Stop logging system
        logger.stop_logging()


if __name__ == "__main__":
    main()
