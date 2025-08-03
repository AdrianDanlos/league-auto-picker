# League Auto Picker

League Auto Picker is an automation utility programm designed to enhance the League of Legends gaming experience by automating repetitive tasks during the champion selection phase.

## Features

- 🤖 **Automated Champion Selection**: Automatically picks champions based on your preferences
- 🚫 **Smart Banning**: Automatically bans specified champions
- ⚡ **Queue Management**: Automatically accepts queue pops
- 🔄 **Position Swapping**: Handles position and pick order swaps by trying to get your preferred role and pick as late as possible.
- 💬 **Communication**: Sends custom messages during the selection phase
- 📊 **LP Tracking**: Automatically tracks LP changes before and after games
- ⚙️ **Configurable**: Easy-to-use configuration system

## Requirements

- **League of Legends Client** (must be running)
- **Python 3.8+**
- **Windows OS** (currently optimized for Windows)

## Setup Instructions

1. **Install Python**

   Download and install Python (version 3.8 or higher recommended) from the [official website](https://www.python.org/downloads/).

2. **Create and Activate a Virtual Environment**

   Open a terminal or command prompt in the project directory and run:

   ```
   py -m venv venv
   ```

   Activate the virtual environment:

   - On **Windows**:
     ```
     venv\Scripts\activate
     ```
   - On **macOS/Linux**:
     ```
     source venv/bin/activate
     ```

3. **Install Dependencies**

   ```
   pip install -r requirements.txt
   ```

4. **Run the script**
   ```
   py .\entrypoint.py
   ```

## Logging System

The application now includes a simple logging system that automatically redirects all console output to a log file. Here's how it works:

### Log Files

- **Location**: `logs/league_auto_picker.log`
- **Format**: Timestamped entries with format `[YYYY-MM-DD HH:MM:SS] message`
- **Content**: All console prints are automatically logged to this file

### Features

- ✅ **Automatic Logging**: All `print()` statements are automatically logged
- ✅ **Timestamped Entries**: Each log entry includes a timestamp
- ✅ **Dual Output**: Logs appear both in console and log file
- ✅ **Thread-Safe**: Works with multi-threaded operations
- ✅ **Graceful Cleanup**: Properly closes log files on exit

### Testing the Logging System

You can test the logging functionality by running:

```
py test_logging.py
```

This will create sample log entries and show you how the system works.

## LP Tracking System

The application now includes an automatic LP tracking system that monitors your ranked progress.

### How It Works

- **Pre-Game**: Saves your current LP when champion select begins
- **Post-Game**: Updates LP data after the game ends
- **History**: Stores all LP changes in `lp_history.json`
- **Queue Support**: Tracks both Solo Queue and Flex Queue separately

### LP History File

- **Location**: `lp_history.json` (in project root)
- **Format**: JSON array of game records
- **Data**: Timestamp, queue type, pre/post LP, LP change, game result

## Last Game Analysis

The application now includes functionality to analyze your most recent game and extract key statistics.

### Features

- **Win/Loss Status**: Determines if you won or lost the game
- **Champion Information**: Shows which champion you played and their spells
- **KDA Statistics**: Provides kills, deaths, assists, and KDA ratio
- **Game Details**: Includes game duration, mode, and queue information

### Usage

```python
from features.lp_tracker import get_last_game_data

# Get last game analysis
result = get_last_game_data()

if "error" not in result:
    # Access the data
    win_loss = result["win_loss"]      # {"won": True, "result": "Victory"}
    champion = result["champion"]       # {"champion_name": "Yasuo", "champion_id": 157}
    kda = result["kda"]                # {"kills": 10, "deaths": 2, "assists": 5, "kda_display": "10/2/5"}

    print(f"Result: {win_loss['result']}")
    print(f"Champion: {champion['champion_name']}")
    print(f"KDA: {kda['kda_display']}")
else:
    print(f"Error: {result['error']}")
```

### Testing

Run the test script to see the analysis in action:

```
python test_last_game.py
```

### Viewing LP History

You can view your LP history using the utility script:

```
py view_lp_history.py
```

This will show:

- Last 10 games with LP changes
- Total LP change across all tracked games
- Average LP change per game
- Game timestamps and queue types

### LP Tracking Features

- ✅ **Automatic Tracking**: No manual input required
- ✅ **Queue Detection**: Automatically detects Solo vs Flex queue
- ✅ **Persistent Storage**: LP history survives program restarts
- ✅ **Detailed Logging**: LP changes are logged to console and file
- ✅ **Error Handling**: Gracefully handles API errors and missing data

### Example Output

```
📊 Saved pre-game LP: 1250 (RANKED_SOLO_5x5)
📊 LP Change: +18 (1250 → 1268)
```

### Testing LP Tracker

You can test the LP tracking functionality with:

```
py test_lp_tracker.py
```
