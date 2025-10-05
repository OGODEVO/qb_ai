from tools.quickbooks import qb_query, get_tools as get_qb_tools
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query, get_tools as get_meta_ads_tools
from tools.google_calendar import get_tools as get_calendar_tools, list_events, add_event, update_event, delete_event
from tools.document_handler import get_tools as get_document_tools, process_document, suggest_metadata, vectorize_and_store_document
from tools.bm25 import retrieve_files, get_tools as get_bm25_tools
from tools.sportradar import get_tools as get_sportradar_tools, get_daily_schedule, get_game_boxscore, get_game_summary, get_prematch_odds
from .utils import get_remember_fact_tool
from .tool_server import get_tool_servers
import requests

def make_remote_tool(url):
    def remote_tool(**kwargs):
        res = requests.post(url, json=kwargs)
        res.raise_for_status()
        return res.json()
    return remote_tool

def get_tools_and_available_functions():
    """Get the tools and available functions."""
    tools = []
    available_tools = {}

    # # Add the remember_fact tool by default
    # tools.append(get_remember_fact_tool())
    # available_tools["remember_fact"] = ltm.remember_fact

    # TODO: Make tool selection dynamic based on request
    tools.extend(get_qb_tools())
    available_tools["qb_query"] = qb_query

    browser_tool = BrowserTool()
    tools.extend(browser_tool.get_tools())
    available_tools["browser_search"] = browser_tool.search

    tools.extend(get_meta_ads_tools())
    available_tools["meta_ads_query"] = meta_ads_query

    tools.extend(get_calendar_tools())
    available_tools["list_events"] = list_events
    available_tools["add_event"] = add_event
    available_tools["update_event"] = update_event
    available_tools["delete_event"] = delete_event

    tools.extend(get_document_tools())
    available_tools["process_document"] = process_document
    available_tools["suggest_metadata"] = suggest_metadata
    available_tools["vectorize_and_store_document"] = vectorize_and_store_document

    tools.extend(get_bm25_tools())
    available_tools["retrieve_files"] = retrieve_files

    tools.extend(get_sportradar_tools())
    available_tools["get_daily_schedule"] = get_daily_schedule
    available_tools["get_game_boxscore"] = get_game_boxscore
    available_tools["get_game_summary"] = get_game_summary
    available_tools["get_prematch_odds"] = get_prematch_odds

    tool_servers = get_tool_servers()
    for server in tool_servers:
        try:
            response = requests.get(server["url"])
            response.raise_for_status()
            server_tools = response.json()
            if "tools" in server_tools:
                tools.extend(server_tools["tools"])
            if "available_tools" in server_tools:
                for func_name, func_url in server_tools["available_tools"].items():
                    available_tools[func_name] = make_remote_tool(func_url)
        except Exception as e:
            print(f"Error loading tools from server {server['url']}: {e}")

    return tools, available_tools
