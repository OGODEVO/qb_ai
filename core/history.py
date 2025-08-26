import json
import os
from datetime import datetime, timedelta

HISTORY_FILE = "chat_history.json"
RETENTION_HOURS = 72

def save_history(messages: list[dict]):
    """
    Saves the chat history to a JSON file with timestamps.

    Args:
        messages (list[dict]): The list of chat messages to save.
    """
    with open(HISTORY_FILE, "w") as f:
        history = {
            "messages": messages,
            "timestamp": datetime.now().isoformat()
        }
        json.dump(history, f, indent=2)

def load_history() -> list[dict]:
    """
    Loads the chat history from the JSON file if it's within the retention period.

    Returns:
        list[dict]: The list of chat messages, or an empty list if the history is stale or doesn't exist.
    """
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
            timestamp_str = history.get("timestamp")
            if not timestamp_str:
                return []

            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.now() - timestamp > timedelta(hours=RETENTION_HOURS):
                # History is stale, return empty list
                return []
            
            return history.get("messages", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []
