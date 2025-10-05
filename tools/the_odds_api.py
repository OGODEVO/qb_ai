import os
import requests
from dotenv import load_dotenv

load_dotenv()

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"

def get_odds(sport: str, regions: str = "us", markets: str = "h2h"):
    """
    Fetches odds for a given sport from The Odds API.

    Args:
        sport: The sport key (e.g., basketball_nba).
        regions: The region for the odds (e.g., us, uk, eu, au). Defaults to us.
        markets: The market for the odds (e.g., h2h, spreads, totals). Defaults to h2h (head-to-head).
    """
    if not THE_ODDS_API_KEY:
        return "The Odds API key not found. Please add it to your .env file."

    odds_response = requests.get(f"{BASE_URL}/sports/{sport}/odds?api_key={THE_ODDS_API_KEY}&regions={regions}&markets={markets}")
    odds_response.raise_for_status()
    return odds_response.json()

def get_tools():
    """
    Returns a list of tools for The Odds API.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_odds",
                "description": "Fetches odds for a given sport from The Odds API.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sport": {
                            "type": "string",
                            "description": "The sport key (e.g., basketball_nba)."
                        },
                        "regions": {
                            "type": "string",
                            "description": "The region for the odds (e.g., us, uk, eu, au). Defaults to us."
                        },
                        "markets": {
                            "type": "string",
                            "description": "The market for the odds (e.g., h2h, spreads, totals). Defaults to h2h."
                        }
                    },
                    "required": ["sport"],
                },
            },
        },
    ]
