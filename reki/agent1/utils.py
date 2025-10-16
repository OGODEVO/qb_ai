"""
This module provides utility functions for the application.
"""

import os
import logging
import google.generativeai as genai
import json
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger('self_improvement_logger')

async def make_api_call(client, **kwargs):
    """Makes an API call to the specified client and model."""
    if kwargs.get("stream"):
        return await client.chat.completions.create(**kwargs)
    else:
        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message

async def make_gemini_api_call(model, system_instruction=None, **kwargs):
    """Makes an API call to the Gemini API."""
    try:
        model_args = {}
        if system_instruction:
            model_args['system_instruction'] = system_instruction
        
        gemini_model = genai.GenerativeModel(model, **model_args)
        
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

def convert_messages_to_gemini_format(messages):
    """Converts a list of OpenAI-formatted messages to the Gemini format."""
    gemini_messages = []
    for message in messages:
        role = message.get("role")
        if role == "assistant":
            role = "model"
        
        if role not in ["user", "model", "tool"]:
            continue

        parts = []
        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, TypeError):
                    args = tc["function"]["arguments"]

                parts.append({
                    "function_call": {
                        "name": tc["function"]["name"],
                        "args": args
                    }
                })
            gemini_messages.append({"role": "model", "parts": parts})
        elif role == "tool":
            try:
                response_content = json.loads(message["content"])
            except (json.JSONDecodeError, TypeError):
                response_content = message["content"]
                
            parts.append({
                "function_response": {
                    "name": message.get("name") or message.get("tool_code"),
                    "response": response_content
                }
            })
            gemini_messages.append({"role": "tool", "parts": parts})
        elif message.get("content") is not None:
            parts.append({"text": message["content"]})
            gemini_messages.append({"role": role, "parts": parts})
            
    return gemini_messages
