# League Auto Picker

League Auto Picker is an automation utility programm designed to enhance the League of Legends gaming experience by automating repetitive tasks during the champion selection phase.

## Features

- 🤖 **Automated Champion Selection**: Automatically picks champions based on your preferences and counter picks
- 🚫 **Smart Banning**: Automatically bans specified champions
- ⚡ **Queue Management**: Automatically accepts queue pops
- 🔄 **Position Swapping**: Handles position and pick order swaps by trying to get your preferred role and pick as late as possible. (Trying to pick as late as possible is only applyable for top and mid)
- 🛡️ **Auto-Decline Swaps**: Automatically declines incoming swap requests, trades, and position swaps after a couple of seconds
- 💬 **Communication**: Sends custom messages during the selection phase
- 🔮 **Smart Runes & Summoner Spells**: Automatically selects optimal runes and summoner spells for your champion
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

1. First, it checks if any enemy picked a champion you have a counter for and selects your counter pick (if multiple champions can counter the same enemy, it picks the one where that enemy appears earliest in your counter list)
2. If no counters apply, it picks from your "DEFAULT" list for that role (Useful when you always want to pick a specific champion in case we are blindpicking)
3. If "random_mode_active" is true, it randomly selects from your "RANDOM_MODE" pool instead of using the first default champion. (Useful to be able to play a variety of champions whenever we are blindpicking)

**Summoner spells**: You can set default summoner spells for each role, and override them by specifying champion-specific summoner spells for that role.

**Messages**: You can define multiple messages and the bot will randomly select one to send whenever the champ select starts. If the messages are empty it will by default send the message: 'hey happy friday' (in case today is friday)

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
