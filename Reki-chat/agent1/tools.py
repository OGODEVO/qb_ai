from tools.quickbooks import qb_query, get_tools as get_qb_tools
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query, get_tools as get_meta_ads_tools
from tools.google_calendar import get_tools as get_calendar_tools, list_events, add_event, update_event, delete_event
from .utils import get_remember_fact_tool

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
    
    return tools, available_tools
