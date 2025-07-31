# League Auto Picker

League Auto Picker is an automation utility programm designed to enhance the League of Legends gaming experience by automating repetitive tasks during the champion selection phase.

## Features

- 🤖 **Automated Champion Selection**: Automatically picks champions based on your preferences
- 🚫 **Smart Banning**: Automatically bans specified champions
- ⚡ **Queue Management**: Automatically accepts queue pops
- 🔄 **Position Swapping**: Handles position and pick order swaps by trying to get your preferred role and pick as late as possible.
- 💬 **Communication**: Sends custom messages during the selection phase
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
