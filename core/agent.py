import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

from tools.quickbooks import qb_query, get_tools as get_qb_tools
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query, get_tools as get_meta_ads_tools
from tools.google_calendar import get_tools as get_calendar_tools, list_events, add_event, update_event, delete_event
from core.memory import LongTermMemory
from core.short_term_memory import ShortTermMemory
from core.utils import make_api_call, get_current_time, get_remember_fact_tool

# --- Initialization ---
load_dotenv(override=True)

# --- Load Models and Tools ---
def load_long_term_memory():
    """Load the long-term memory store."""
    return LongTermMemory()

ltm = load_long_term_memory()

try:
    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url=os.environ["XAI_BASE_URL"],
    )
    ollama_client = OpenAI(
        api_key="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    )
except KeyError:
    raise RuntimeError("Missing xAI credentials. Please set XAI_API_KEY and XAI_BASE_URL in your .env file.")

# --- System Prompt and Tools ---
try:
    with open("prompts/system.txt", "r") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    raise RuntimeError("System prompt file not found at 'prompts/system.txt'.")

def get_tools_and_available_functions():
    """Get the tools and available functions."""
    tools = []
    available_tools = {}

    # Add the remember_fact tool by default
    tools.append(get_remember_fact_tool())
    available_tools["remember_fact"] = ltm.remember_fact

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

def handle_chat_completion(short_term_memory: ShortTermMemory, model: str, stream: bool = False):
    """Handles the chat completion logic."""
    tools, available_tools = get_tools_and_available_functions()

    messages = short_term_memory.get_history()

    # Query long-term memory
    last_user_message = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)
    if last_user_message:
        retrieved_memories = ltm.query_memory(last_user_message)
    else:
        retrieved_memories = []

    # Construct the system prompt with LTM if available
    system_prompt = BASE_SYSTEM_PROMPT.format(current_time=get_current_time())
    if retrieved_memories:
        memory_summaries = [mem.get('summary', '') for mem in retrieved_memories]
        system_prompt += "\n\n--- Relevant Memories---" + "\n".join(memory_summaries)

    # Prepend system prompt
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    if stream:
        def stream_generator():
            stream_response = make_api_call(
                client=client,
                model=model,
                messages=final_messages,
                tools=tools,
                tool_choice="auto",
                stream=True
            )
            for chunk in stream_response:
                yield chunk.choices[0].delta.content or ""
        return stream_generator()

    response_message = make_api_call(
        client=client,
        model=model,
        messages=final_messages,
        tools=tools,
        tool_choice="auto"
    )

    if not response_message.tool_calls:
        return response_message

    final_messages.append(response_message)
    # short_term_memory.add_message(response_message.role, response_message.content)

    for tool_call in response_message.tool_calls:
        function_name = tool_call.function.name
        function_to_call = available_tools.get(function_name)
        if function_to_call:
            try:
                function_args = json.loads(tool_call.function.arguments)
                function_response = function_to_call(**function_args)
                tool_response_content = json.dumps(function_response)
                final_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_response_content,
                })
                # short_term_memory.add_message("tool", tool_response_content)
            except Exception as e:
                error_content = json.dumps({"error": str(e)})
                final_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": error_content,
                })
                # short_term_memory.add_message("tool", error_content)

    # Second API call to get the final response from the assistant
    final_response = make_api_call(
        client=client,
        model=model,
        messages=final_messages,
        tools=tools,
        tool_choice="auto"
    )

    return final_response
