
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

def handle_chat_completion(messages, model, stream=False):
    """Handles the chat completion logic."""
    tools, available_tools = get_tools_and_available_functions()

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

    # === Primary API Call ===
    api_call_args = {
        "model": model,
        "messages": final_messages,
    }
    if tools:
        api_call_args["tools"] = tools
        api_call_args["tool_choice"] = "auto"

    start_time = time.time()
    response_message = make_api_call(
        client=client,
        **api_call_args,
    )
    end_time = time.time()
    print(f"X.AI API call latency: {end_time - start_time:.2f} seconds")

    tool_calls = response_message.tool_calls

    # === Tool-Calling Logic ===
    if tool_calls:
        final_messages.append(response_message)
        executed_tool_calls = set()

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_tools.get(function_name)
            
            if not function_to_call:
                # In a real-world scenario, you might want to handle this more gracefully
                raise Exception(f"Model tried to call an unknown function: {function_name}")

            try:
                function_args = json.loads(tool_call.function.arguments)
                tool_call_identifier = f"{function_name}-{json.dumps(function_args, sort_keys=True)}"

                if tool_call_identifier in executed_tool_calls:
                    continue # Skip duplicate tool calls
                
                executed_tool_calls.add(tool_call_identifier)
                
                function_response = function_to_call(**function_args)

                final_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_response),
                    }
                )
            except json.JSONDecodeError:
                # Handle JSON decoding errors
                raise Exception(f"Invalid arguments from model for {function_name}: {tool_call.function.arguments}")
            except Exception as e:
                final_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": str(e)}),
                    }
                )

        # === Secondary API Call (with tool results) ===
        start_time = time.time()
        final_response_obj = make_api_call(
            client=client,
            model=model,
            messages=final_messages,
        )
        end_time = time.time()
        print(f"X.AI API call latency (with tools): {end_time - start_time:.2f} seconds")
        return final_response_obj

    # === Standard Response (no tool call) ===
    else:
        return response_message
