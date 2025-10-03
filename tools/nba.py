from nba_api.stats.endpoints import playercareerstats, scoreboardv2, boxscoreadvancedv2, playbyplayv2
from nba_api.live.nba.endpoints import scoreboard, odds

def get_player_career_stats(player_id: str):
    """
    Get the career stats for a given player.
    """
    career = playercareerstats.PlayerCareerStats(player_id=player_id)
    return career.get_dict()

def get_live_scoreboard():
    """
    Get the live scoreboard for today's games.
    """
    games = scoreboard.ScoreBoard()
    return games.get_dict()

def get_scoreboard(day_offset: int, game_date: str, league_id: str):
    """
    Get the scoreboard for a given date.
    """
    return scoreboardv2.ScoreboardV2(day_offset=day_offset, game_date=game_date, league_id=league_id).get_dict()

def get_boxscore_advanced(game_id: str, end_period: int, end_range: int, range_type: int, start_period: int, start_range: int):
    """
    Get the advanced box score for a given game.
    """
    return boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id, end_period=end_period, end_range=end_range, range_type=range_type, start_period=start_period, start_range=start_range).get_dict()

def get_play_by_play(game_id: str, end_period: int, start_period: int):
    """
    Get the play-by-play data for a given game.
    """
    return playbyplayv2.PlayByPlayV2(game_id=game_id, end_period=end_period, start_period=start_period).get_dict()

def get_odds():
    """
    Get the odds for today's games.
    """
    return odds.Odds().get_dict()

def get_tools() -> list[dict]:
    """Returns the tool definition for the nba functions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_player_career_stats",
                "description": "Get the career stats for a given player.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "player_id": {
                            "type": "string",
                            "description": "The ID of the player."
                        }
                    },
                    "required": ["player_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_live_scoreboard",
                "description": "Get the live scoreboard for today's games.",
                "parameters": {},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scoreboard",
                "description": "Get the scoreboard for a given date. This includes game status, team and player information, and scores.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "day_offset": {
                            "type": "integer",
                            "description": "The offset from today."
                        },
                        "game_date": {
                            "type": "string",
                            "description": "The date of the games."
                        },
                        "league_id": {
                            "type": "string",
                            "description": "The league ID."
                        }
                    },
                    "required": ["day_offset", "game_date", "league_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_boxscore_advanced",
                "description": "Get the advanced box score for a given game. This includes advanced stats like offensive/defensive ratings, pace, and Player Impact Estimate (PIE).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "game_id": {
                            "type": "string",
                            "description": "The ID of the game."
                        },
                        "end_period": {
                            "type": "integer",
                            "description": "The end period of the game."
                        },
                        "end_range": {
                            "type": "integer",
                            "description": "The end range of the game."
                        },
                        "range_type": {
                            "type": "integer",
                            "description": "The range type of the game."
                        },
                        "start_period": {
                            "type": "integer",
                            "description": "The start period of the game."
                        },
                        "start_range": {
                            "type": "integer",
                            "description": "The start range of the game."
                        }
                    },
                    "required": ["game_id", "end_period", "end_range", "range_type", "start_period", "start_range"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_play_by_play",
                "description": "Get detailed play-by-play data for a given game. This includes descriptions of each event, players involved, and the score at the time of the event.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "game_id": {
                            "type": "string",
                            "description": "The ID of the game."
                        },
                        "end_period": {
                            "type": "integer",
                            "description": "The end period of the game."
                        },
                        "start_period": {
                            "type": "integer",
                            "description": "The start period of the game."
                        }
                    },
                    "required": ["game_id", "end_period", "start_period"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_odds",
                "description": "Get betting odds for today's games from various sportsbooks. This includes spread, moneyline, and total score odds.",
                "parameters": {},
            },
        },
    ]