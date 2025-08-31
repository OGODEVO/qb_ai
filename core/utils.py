"""
This module provides utility functions for the application.
"""

import os
from datetime import datetime

def get_project_root():
    """
    Returns the absolute path of the project root directory.
    """
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def get_current_time():
    """
    Returns the current date and time as a formatted string.
    """
    return datetime.now().strftime("%A, %B %d, %Y %I:%M %p")

def get_remember_fact_tool():
    """
    Returns the 'remember_fact' tool definition.
    """
    return {
        "type": "function",
        "function": {
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
        },
    }