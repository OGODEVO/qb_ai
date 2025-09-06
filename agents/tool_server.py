import json
import os
from typing import Dict, List
import requests


TOOL_SERVER_CONFIG_FILE = "tool_servers.json"

def validate_url(url: str) -> bool:
    """
    Validates the URL by trying to fetch the content.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        json.loads(response.text)
        return True
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return False

def get_tool_servers() -> List[Dict]:
    """
    Loads the tool server configurations from the JSON file.
    """
    if not os.path.exists(TOOL_SERVER_CONFIG_FILE):
        return []
    with open(TOOL_SERVER_CONFIG_FILE, "r") as f:
        return json.load(f)

def save_tool_servers(servers: List[Dict]) -> None:
    """
    Saves the tool server configurations to the JSON file.
    """
    with open(TOOL_SERVER_CONFIG_FILE, "w") as f:
        json.dump(servers, f, indent=4)

def add_tool_server(url: str) -> None:
    """
    Adds a new tool server to the configuration.
    """
    if not validate_url(url):
        raise ValueError("Invalid tool server URL")
    servers = get_tool_servers()
    servers.append({"url": url})
    save_tool_servers(servers)

def remove_tool_server(index: int) -> None:
    """
    Removes a tool server from the configuration by its index.
    """
    servers = get_tool_servers()
    if 0 <= index < len(servers):
        servers.pop(index)
        save_tool_servers(servers)
