
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SPORTS_GAME_ODDS_API_KEY = os.getenv("SPORTS_GAME_ODDS_API_KEY")
BASE_URL = "https://api.sportsgameodds.com/v2"

def get_odds(event_id: str, market_odd_id: str):
    """
    Fetches odds for a given event and market from the SportsGameOdds API.

    Args:
        event_id: The ID of the event.
        market_odd_id: The specific ID of the market (e.g., points-home-game-ml-home).
    """
    if not SPORTS_GAME_ODDS_API_KEY:
        return "SportsGameOdds API key not found. Please add it to your .env file."

    headers = {"X-Api-Key": SPORTS_GAME_ODDS_API_KEY}
    params = {
        "marketOddId": market_odd_id,
    }
        
    odds_response = requests.get(f"{BASE_URL}/events/{event_id}/odds", headers=headers, params=params)
    odds_response.raise_for_status()
    return odds_response.json()

def get_events(sport_id: str, league_id: str = None, odds_available: bool = True):
    """
    Fetches all events for a given sport from the SportsGameOdds API.

    Args:
        sport_id: The ID of the sport (e.g., BASKETBALL).
        league_id: The ID of the league (e.g., NBA).
        odds_available: Whether to filter for events with available odds.
    """
    if not SPORTS_GAME_ODDS_API_KEY:
        return "SportsGameOdds API key not found. Please add it to your .env file."

    headers = {"X-Api-Key": SPORTS_GAME_ODDS_API_KEY}
    params = {
        "sportID": sport_id,
        "oddsAvailable": str(odds_available).lower()
    }
    if league_id:
        params["leagueID"] = league_id
        
    events_response = requests.get(f"{BASE_URL}/events", headers=headers, params=params)
    events_response.raise_for_status()
    return events_response.json()

def get_sports():
    """
    Fetches the list of available sports from the SportsGameOdds API.
    """
    if not SPORTS_GAME_ODDS_API_KEY:
        return "SportsGameOdds API key not found. Please add it to your .env file."

    headers = {"X-Api-Key": SPORTS_GAME_ODDS_API_KEY}
    sports_response = requests.get(f"{BASE_URL}/sports", headers=headers)
    sports_response.raise_for_status()
    return sports_response.json()

def get_tools():
    """
    Returns a list of tools for the SportsGameOdds API.
    """
    return [
        {
            "function_declarations": [{
                "name": "get_odds",
                "description": "Fetches odds for a given event and a specific market ID from the SportsGameOdds API.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "The ID of the event."
                        },
                        "market_odd_id": {
                            "type": "string",
                            "description": "The specific ID for the market, e.g., 'points-home-game-ml-home' for Home Moneyline."
                        }
                    },
                    "required": ["event_id", "market_odd_id"],
                },
            }]
        },
        {
            "function_declarations": [{
                "name": "get_events",
                "description": "Fetches all events for a given sport from the SportsGameOdds API.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sport_id": {
                            "type": "string",
                            "description": "The ID of the sport (e.g., BASKETBALL)."
                        },
                        "league_id": {
                            "type": "string",
                            "description": "The ID of the league (e.g., NBA)."
                        },
                        "odds_available": {
                            "type": "boolean",
                            "description": "Filter for events that have odds available."
                        }
                    },
                    "required": ["sport_id"],
                },
            }]
        },
        {
            "function_declarations": [{
                "name": "get_sports",
                "description": "Fetches the list of available sports from the SportsGameOdds API.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }]
        },
    ]
