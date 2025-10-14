import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

from collections import namedtuple
from .tools import get_tools_and_available_functions
from .short_term_memory import ShortTermMemory
from .utils import make_api_call, get_current_time

# Mock objects to wrap messages for API compatibility
Choice = namedtuple('Choice', ['message'])
Completion = namedtuple('Completion', ['choices'])

# --- Initialization ---
load_dotenv(override=True)

try:
    client = AsyncOpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url=os.environ["XAI_BASE_URL"],
    )
    ollama_client = AsyncOpenAI(
        api_key="ollama",
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    )
    reki_1_client = AsyncOpenAI(
        api_key="no-key-needed",
        base_url="http://localhost:8787/v1",
    )
except KeyError:
    raise RuntimeError("Missing xAI credentials. Please set XAI_API_KEY and XAI_BASE_URL in your .env file.")

# --- System Prompt ---
try:
    with open("agent1/prompt.txt", "r") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    raise RuntimeError("System prompt file not found at 'agent1/prompt.txt'.")

async def handle_chat_completion(short_term_memory: ShortTermMemory, model: str, stream: bool = False):
    """Handles the chat completion logic."""
    tools, available_tools = get_tools_and_available_functions()

    messages = short_term_memory.get_history()

    system_prompt = BASE_SYSTEM_PROMPT.format(current_time=get_current_time())

    # Prepend system prompt
    final_messages = [{"role": "system", "content": system_prompt}] + messages

    # Select client based on model
    if model == "reki-1":
        current_client = reki_1_client
    else:
        current_client = client

    if stream:
        async for chunk in stream_generator(current_client, model, final_messages, tools, available_tools):
            yield chunk
        return

    response_message = await make_api_call(
        client=current_client,
        model=model,
        messages=final_messages,
        tools=tools,
        tool_choice="auto"
    )

    max_turns = 5
    turn_count = 0
    while response_message.tool_calls and turn_count < max_turns:
        final_messages.append(response_message)

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
                except Exception as e:
                    error_content = json.dumps({"error": str(e)})
                    final_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_content,
                    })
        
        response_message = await make_api_call(
            client=client,
            model=model,
            messages=final_messages,
            tools=tools,
            tool_choice="auto"
        )
        turn_count += 1

    yield response_message

async def stream_generator(client, model, messages, tools, available_tools):
    """Generator function to handle streaming responses and tool calls."""
    stream_response = await make_api_call(
        client=client,
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=True
    )

    max_turns = 5
    turn_count = 0
    has_yielded_content = False
    accumulated_tool_calls_args = {} # To accumulate arguments for tool calls by index

    while turn_count < max_turns:
        current_turn_tool_calls = []
        async for chunk in stream_response:
            # Get the relevant data from the chunk
            # Assuming reki-1 provides message directly on choices[0]
            chunk_data = chunk.choices[0].message if hasattr(chunk.choices[0], 'message') else chunk.choices[0]

            # Handle tool calls
            if hasattr(chunk_data, 'tool_calls') and chunk_data.tool_calls:
                for tool_call_chunk in chunk_data.tool_calls:
                    if tool_call_chunk.index not in accumulated_tool_calls_args:
                        accumulated_tool_calls_args[tool_call_chunk.index] = {
                            "id": tool_call_chunk.id,
                            "function": {
                                "name": tool_call_chunk.function.name,
                                "arguments": ""
                            }
                        }
                    accumulated_tool_calls_args[tool_call_chunk.index]["function"]["arguments"] += tool_call_chunk.function.arguments
            
            yield chunk # Yield the original chunk as the client expects it
            has_yielded_content = True

        # After iterating through all chunks for a given turn
        if not accumulated_tool_calls_args: # No tool calls in this turn
            if not has_yielded_content:
                # Handle cases where the model returns an empty stream
                yield Completion(choices=[Choice(message={"role": "assistant", "content": ""})])
            return # Exit if no tool calls and content has been yielded or it's an empty stream

        # Reconstruct the full tool calls from accumulated arguments
        full_tool_calls = []
        for index in sorted(accumulated_tool_calls_args.keys()):
            tc_data = accumulated_tool_calls_args[index]
            # Create a mock object that resembles the expected tool_call structure
            MockToolCall = namedtuple('MockToolCall', ['id', 'function'])
            MockFunction = namedtuple('MockFunction', ['name', 'arguments'])
            full_tool_calls.append(MockToolCall(
                id=tc_data['id'],
                function=MockFunction(
                    name=tc_data['function']['name'],
                    arguments=tc_data['function']['arguments']
                )
            ))
        
        assistant_message = {
            "role": "assistant",
            "content": None, # Content would have been yielded directly
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in full_tool_calls
            ]
        }
        messages.append(assistant_message)

        for tool_call in full_tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_tools.get(function_name)
            if function_to_call:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = function_to_call(**function_args)
                    tool_response_content = json.dumps(function_response)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_response_content,
                    })
                except Exception as e:
                    error_content = json.dumps({"error": str(e)})
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_content,
                    })

        # Reset for the next turn
        accumulated_tool_calls_args = {}
        stream_response = await make_api_call(
            client=client,
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True
        )
        turn_count += 1

        # Reconstruct the full tool calls
        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls
            ]
        }
        messages.append(assistant_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_tools.get(function_name)
            if function_to_call:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    function_response = function_to_call(**function_args)
                    tool_response_content = json.dumps(function_response)
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_response_content,
                    })
                except Exception as e:
                    error_content = json.dumps({"error": str(e)})
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_content,
                    })

        stream_response = await make_api_call(
            client=client,
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=True
        )
        turn_count += 1