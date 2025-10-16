"""
This module provides utility functions for the application.
"""

import os
import logging
import google.generativeai as genai
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger('self_improvement_logger')

async def make_api_call(client, **kwargs):
    """Makes an API call to the specified client and model."""
    try:
        if kwargs.get("stream"):
            return await client.chat.completions.create(**kwargs)
        else:
            response = await client.chat.completions.create(**kwargs)
            return response.choices[0].message
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        return None

async def make_gemini_api_call(model, **kwargs):
    """Makes an API call to the Gemini API."""
    try:
        gemini_model = genai.GenerativeModel(model)
        if kwargs.get("stream"):
            return await gemini_model.generate_content_async(**kwargs)
        else:
            response = await gemini_model.generate_content_async(**kwargs)
            return response
    except Exception as e:
        logger.error(f"Error during Gemini API call: {e}")
        return None

def get_project_root():
    """
    Returns the absolute path of the project root directory.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def get_current_time():
    """
    Returns the current date and time as a formatted string.
    """
    return datetime.now(ZoneInfo("America/Chicago")).strftime("%A, %B %d, %Y %I:%M %p")

def get_remember_fact_tool():
    """
    Returns the 'remember_fact' tool definition.
    """
    return {
        "function_declarations": [{
            "name": "remember_fact",
            "description": "Saves a specific fact or piece of information to the agent's long-term memory. Use this when the user explicitly asks to remember something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The specific fact or piece of information to remember."
                    }
                },
                "required": ["fact"],
            },
        }]
    }
