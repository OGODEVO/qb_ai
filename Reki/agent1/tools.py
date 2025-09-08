from tools.quickbooks import qb_query, get_tools as get_qb_tools
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query, get_tools as get_meta_ads_tools
from tools.google_calendar import get_tools as get_calendar_tools, list_events, add_event, update_event, delete_event
from tools.document_handler import get_tools as get_document_tools, process_document_and_store_in_db, find_similar_documents
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
    available_tools["process_document_and_store_in_db"] = process_document_and_store_in_db
    available_tools["find_similar_documents"] = find_similar_documents

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
