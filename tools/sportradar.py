import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SPORTRADAR_API_KEY = os.getenv("SPORTRADAR_API_KEY")
BASE_URL = "https://api.sportradar.us/nba/production/v8/en"

def get_daily_schedule(date: str = None):
    """
    Fetches the daily schedule for a given date from the Sportradar API.

    Args:
        date: The date for the schedule in YYYY/MM/DD format. Defaults to today.
    """
    if not SPORTRADAR_API_KEY:
        return "Sportradar API key not found. Please add it to your .env file."

    if not date:
        date = datetime.now().strftime("%Y/%m/%d")

    schedule_response = requests.get(f"{BASE_URL}/games/{date}/schedule.json?api_key={SPORTRADAR_API_KEY}")
    schedule_response.raise_for_status()
    return schedule_response.json()

def get_game_boxscore(gameId: str):
    """
    Fetches the boxscore for a given game from the Sportradar API.

    Args:
        gameId: The ID of the game.
    """
    if not SPORTRADAR_API_KEY:
        return "Sportradar API key not found. Please add it to your .env file."

    boxscore_response = requests.get(f"{BASE_URL}/games/{gameId}/boxscore.json?api_key={SPORTRADAR_API_KEY}")
    boxscore_response.raise_for_status()
    return boxscore_response.json()

def get_game_summary(gameId: str):
    """
    Fetches the game summary for a given game from the Sportradar API.

    Args:
        gameId: The ID of the game.
    """
    if not SPORTRADAR_API_KEY:
        return "Sportradar API key not found. Please add it to your .env file."

    summary_response = requests.get(f"{BASE_URL}/games/{gameId}/summary.json?api_key={SPORTRADAR_API_KEY}")
    summary_response.raise_for_status()
    return summary_response.json()

def get_tools():
    """
    Returns a list of tools for the Sportradar API.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_daily_schedule",
                "description": "Fetches the daily schedule for a given date from the Sportradar API. This includes game IDs, which can be used to get more detailed information about a specific game.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "The date for the schedule in YYYY/MM/DD format. Defaults to today."
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_game_boxscore",
                "description": "Fetches the boxscore for a given game from the Sportradar API. This provides detailed statistical data for a completed or in-progress game, including team and player stats.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "gameId": {
                            "type": "string",
                            "description": "The ID of the game."
                        }
                    },
                    "required": ["gameId"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_game_summary",
                "description": "Fetches the game summary for a given game from the Sportradar API. This includes top-level boxscore information and detailed game stats for teams and players.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "gameId": {
                            "type": "string",
                            "description": "The ID of the game."
                        }
                    },
                    "required": ["gameId"],
                },
            },
        },
    ]
