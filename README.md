# League Auto Picker

League Auto Picker is an automation utility programm designed to enhance the League of Legends gaming experience by automating repetitive tasks during the champion selection phase.

## Features

- 🤖 **Automated Champion Selection**: Automatically picks champions based on your preferences and counter picks
- 🔁 **Manual Counter Cycling**: Press a hotkey during your pick turn to move from best counter to 2nd/3rd options, then fall back to defaults
- 🚫 **Smart Banning**: Automatically bans specified champions
- ⚡ **Queue Management**: Automatically accepts queue pops
- 🔄 **Position Swapping**: Handles position and pick order swaps by trying to get your preferred role and pick as late as possible. (Trying to pick as late as possible is only applyable for top and mid)
- 🛡️ **Auto-Decline Swaps**: Automatically declines incoming swap requests, trades, and position swaps after a couple of seconds
- 💬 **Communication**: Sends custom messages during the selection phase
- 🔮 **Smart Runes & Summoner Spells**: Automatically selects optimal runes and summoner spells for your champion (runes can be toggled off)
- 📢 **Discord Integration**: Sends detailed pre-game and post-game notifications to Discord
- 📊 **LP Tracking**: Automatically tracks LP changes before and after games
- ⚙️ **Configurable**: Easy-to-use configuration system

## Setup Instructions

1. **Install Python**

   Download and install Python (version 3.8 or higher recommended) from the [official website](https://www.python.org/downloads/).

2. **Create and Activate a Virtual Environment**

   Open a terminal or command prompt in the project directory and run the following commands to create a virtual environment, activate it and install the needed dependencies:

   ```
   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Setup config file with your own preferences

For reference check the `config.example.json` file. Once you have updated it rename it to `config.json` and you are ready to go.

More information about the `config.json` file:

**Picks Section**: The bot follows this priority order when picking champions:

1. First, it builds a ranked counter list from best to worst (global ranking based on matchup position in your counter lists)
2. During your pick turn, press the configured `cycle_counter_hotkey` (default: `f8`) to move to the next ranked counter
3. After counters are exhausted, cycling continues through your "DEFAULT" list for that role in order
4. If "random_mode_active" is true, it randomly selects from your "RANDOM_MODE" pool instead of using the first default champion. (Useful to be able to play a variety of champions whenever we are blindpicking)

**Manual counter cycling hotkey**:

- Add `cycle_counter_hotkey` to `config.json` (example: `"cycle_counter_hotkey": "f8"`).
- Press it while your pick is in progress to advance to the next available candidate.

**Summoner spells**: You can set default summoner spells for each role, and override them by specifying champion-specific summoner spells for that role.

**Rune auto-select toggle**:

- Add `autoselect_runes` to `config.json` (example: `"autoselect_runes": true`).
- Set it to `false` if you do not want the bot to auto-set runes after locking a champion.

**Messages**: You can define multiple messages and the bot will randomly select one to send during champ select. If the messages list is empty, the bot skips sending a chat message.

## Summoner Spell IDs

Common summoner spell IDs:

- Flash: `4`
- Teleport: `12`
- Ignite: `14`
- Heal: `3`
- Barrier: `21`
- Exhaust: `3`
- Smite: `11`
- Ghost: `6`

## **Run the script**

```
py .\entrypoint.py
```

## Logging System

The application includes a simple logging system that automatically redirects all console output to a log file.

## Debug Tips

### 1. Session Data Structure

In case we don't know what the data structure looks like, output the whole session:

```python
import json
print(f"Session data: {json.dumps(session_data, indent=2)}")
```

### 2. Traceback Debugging

For debugging purposes, use this to get full traceback information:

```python
import traceback
print(f"⚠️ Full traceback: {traceback.format_exc()}")
```
