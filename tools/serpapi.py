import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

def search(query: str) -> str:
    """
    Searches the web using SerpApi's Google Search.

    Args:
        query: The search query.

    Returns:
        A string containing the search results.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("SERPAPI_API_KEY environment variable not set.")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    return str(results)

def get_tools():
    """Returns a list of tools for SerpApi."""
    return [
        {
            "type": "function",
            "function": {
                "name": "serpapi_search",
                "description": "Leverages the SerpApi service to conduct real-time, comprehensive Google searches. This tool is ideal for accessing up-to-date information, answering questions about current events, or finding specific details on a wide range of topics by querying the Google search engine.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query.",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]