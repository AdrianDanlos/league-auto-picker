# League Auto Picker

League Auto Picker is an automation utility programm designed to enhance the League of Legends gaming experience by automating repetitive tasks during the champion selection phase.

## Features

- 🤖 **Automated Champion Selection**: Automatically picks champions based on your preferences and counter picks
- 🚫 **Smart Banning**: Automatically bans specified champions
- ⚡ **Queue Management**: Automatically accepts queue pops
- 🔄 **Position Swapping**: Handles position and pick order swaps by trying to get your preferred role and pick as late as possible
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

## **Run the script**
   ```
   py .\entrypoint.py
   ```
## TODO: ADD STUFF HERE
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
