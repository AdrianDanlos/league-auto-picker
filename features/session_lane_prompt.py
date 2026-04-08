import threading
import time

try:
    import tkinter as tk
    from tkinter import ttk

    _tk_available = True
except Exception:
    tk = None
    ttk = None
    _tk_available = False


LANE_OPTIONS = ["top", "jungle", "middle", "bottom", "utility"]

_lock = threading.Lock()
_is_prompt_active = False
_selected_role = None
_selected_champ_select_message = None
_root = None
_dismiss_reason = None


def _normalize_role(role):
    if not role:
        return None
    normalized = str(role).strip().lower()
    return normalized if normalized in LANE_OPTIONS else None


def prompt_session_lane_selection(default_role):
    """Show a non-blocking lane prompt in a background UI thread."""
    global _is_prompt_active, _selected_role, _selected_champ_select_message, _dismiss_reason

    if not _tk_available:
        return

    with _lock:
        if _is_prompt_active:
            return
        _is_prompt_active = True
        _selected_role = None
        _selected_champ_select_message = None
        _dismiss_reason = None

    prompt_thread = threading.Thread(
        target=_run_prompt_window,
        args=(default_role,),
        daemon=True,
    )
    prompt_thread.start()


def dismiss_lane_prompt(reason="game_found"):
    """
    Close the lane prompt without applying session overrides.

    reason:
      - game_found: match reached champion select before the user confirmed.
      - lobby_exit: user left the lobby (e.g. home) before confirming.
    """
    global _is_prompt_active, _dismiss_reason, _selected_role, _selected_champ_select_message

    with _lock:
        if not _is_prompt_active:
            return
        _is_prompt_active = False
        _dismiss_reason = reason
        _selected_role = None
        _selected_champ_select_message = None
        current_root = _root

    if current_root:
        try:
            current_root.after(0, current_root.destroy)
        except Exception:
            pass


def dismiss_lane_prompt_for_game_found():
    """Dismiss when champion select starts before the user confirmed."""
    dismiss_lane_prompt("game_found")


def dismiss_lane_prompt_for_lobby_exit():
    """Dismiss when the client returns to home while the prompt is still open."""
    dismiss_lane_prompt("lobby_exit")


def consume_session_preferred_role(config_preferred_role, wait_for_selection_seconds=0):
    """
    Return selected role for this session (if any), otherwise config role.

    The selected role is consumed once so it only applies to one session.
    """
    global _selected_role

    if wait_for_selection_seconds and wait_for_selection_seconds > 0:
        deadline = time.time() + wait_for_selection_seconds
        while time.time() < deadline:
            with _lock:
                if _selected_role:
                    selected = _selected_role
                    _selected_role = None
                    return selected
                is_prompt_active = _is_prompt_active
            if not is_prompt_active:
                break
            time.sleep(0.2)

    with _lock:
        if _selected_role:
            selected = _selected_role
            _selected_role = None
            return selected
    return _normalize_role(config_preferred_role) or "middle"


def consume_session_champ_select_message():
    """
    Return a custom champ-select chat message for this session (if any), else None.

    None means use config.json \"messages\" as today. The value is consumed once.
    """
    global _selected_champ_select_message

    with _lock:
        if _selected_champ_select_message is None:
            return None
        msg = _selected_champ_select_message
        _selected_champ_select_message = None
    stripped = msg.strip() if isinstance(msg, str) else ""
    return stripped if stripped else None


def _run_prompt_window(default_role):
    global _root, _is_prompt_active, _selected_role, _selected_champ_select_message, _dismiss_reason

    default_value = _normalize_role(default_role) or "middle"

    try:
        root = tk.Tk()
        root.title("Select preferred lane")
        root.resizable(False, False)
        root.attributes("-topmost", True)
    except Exception as e:
        with _lock:
            _is_prompt_active = False
            _root = None
        print(f"⚠️ Could not show lane selection prompt: {e}")
        return

    with _lock:
        if not _is_prompt_active:
            root.destroy()
            return
        _root = root

    selected_lane = tk.StringVar(value=default_value)

    container = ttk.Frame(root, padding=12)
    container.grid(row=0, column=0, sticky="nsew")

    ttk.Label(
        container,
        text="Pick your lane for this game:",
    ).grid(row=0, column=0, pady=(0, 8), sticky="w")

    dropdown = ttk.Combobox(
        container,
        textvariable=selected_lane,
        values=LANE_OPTIONS,
        state="readonly",
        width=16,
    )
    dropdown.grid(row=1, column=0, pady=(0, 8), sticky="ew")
    dropdown.focus_set()

    ttk.Label(
        container,
        text="Champ select chat (optional — leave empty for config messages):",
        wraplength=320,
    ).grid(row=2, column=0, pady=(0, 4), sticky="w")

    chat_message_var = tk.StringVar(value="")
    chat_entry = ttk.Entry(container, textvariable=chat_message_var, width=40)
    chat_entry.grid(row=3, column=0, pady=(0, 10), sticky="ew")

    def on_confirm():
        global _is_prompt_active, _selected_role, _selected_champ_select_message, _dismiss_reason
        with _lock:
            if not _is_prompt_active:
                return
            _selected_role = _normalize_role(selected_lane.get())
            raw_msg = chat_message_var.get()
            _selected_champ_select_message = (
                raw_msg.strip() if isinstance(raw_msg, str) and raw_msg.strip() else None
            )
            _is_prompt_active = False
            _dismiss_reason = "selected"
        print(f"✅ Session lane selected: {_selected_role}")
        root.destroy()

    def on_window_close():
        # Keep prompt active until user confirms, champ select starts, or lobby is left.
        return

    ttk.Button(container, text="Use lane", command=on_confirm).grid(
        row=4, column=0, sticky="e"
    )

    root.protocol("WM_DELETE_WINDOW", on_window_close)
    root.mainloop()

    with _lock:
        _root = None
        if _dismiss_reason == "game_found":
            print(
                "🎮 Game found before lane selection. Using preferred_role from config.json."
            )
        elif _dismiss_reason == "lobby_exit":
            print(
                "🔄 Left lobby before lane selection. Using preferred_role from config.json."
            )
