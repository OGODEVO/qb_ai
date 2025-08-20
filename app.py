import os
import json
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from tools.quickbooks import qb_query

# --- Initialization ---
load_dotenv()

# Page config
st.set_page_config(
    page_title="QuickBooks Financial Advisor Agent",
    page_icon="💰",
    layout="centered",
)

# Title
st.title("QuickBooks Financial Advisor Agent")

# --- Sidebar for options ---
with st.sidebar:
    st.header("Options")
    verbose = st.checkbox("Verbose Mode", help="If checked, the agent will show its reasoning and tool calls.")


# --- OpenAI Client Setup ---
# If using a provider other than xAI, update the client initialization.
# For LiteLLM, you might use: from litellm import completion
try:
    client = OpenAI(
        api_key=os.environ["XAI_API_KEY"],
        base_url=os.environ["XAI_BASE_URL"],
    )
except KeyError:
    st.error(
        "Missing xAI credentials. Please set XAI_API_KEY and XAI_BASE_URL in your .env file."
    )
    st.stop()

# --- System Prompt and Tools ---
try:
    with open("prompts/system.txt", "r") as f:
        SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    st.error("System prompt file not found at 'prompts/system.txt'.")
    st.stop()

# OpenAI-style tool definition for our qb_query function
tools = [
    {
        "type": "function",
        "function": {
            "name": "qb_query",
            "description": "Query QuickBooks for financial data like expenses, revenue, and reports.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report": {
                        "type": "string",
                        "enum": ["pnl", "by_category", "expenses_by_vendor", "trial_balance", "custom"],
                        "description": "The type of report to generate."
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "The start date for the report (YYYY-MM-DD)."
                    },
                    "end_date": {
                        "type": "string",
                        "format": "date",
                        "description": "The end date for the report (YYYY-MM-DD)."
                    },
                    "filters": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string"},
                            "vendor": {"type": "string"},
                            "category": {"type": "string"},
                            "search": {"type": "string"},
                            "limit": {"type": "integer"},
                            "group_by": {"type": "string", "enum": ["vendor", "category"]},
                            "compare": {"type": "string", "enum": ["prior_period"]},
                        },
                        "description": "Optional filters to apply to the query."
                    }
                },
                "required": ["report", "start_date", "end_date"],
            },
        },
    }
]

available_tools = {"qb_query": qb_query}

# --- Chat UI and Logic ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("How much did we spend on advertising last month?"):
    # Add user message to history and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Start assistant's turn
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        thinking_message = "Thinking..."
        message_placeholder.markdown(thinking_message + "▌")

        # Construct messages for API call
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

        if verbose:
            with st.expander("Initial API Call Messages"):
                st.json(api_messages)

        # === Primary API Call ===
        response = client.chat.completions.create(
            model=os.getenv("XAI_MODEL", "grok-4"),
            messages=api_messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # === Tool-Calling Logic ===
        if tool_calls:
            if verbose:
                with st.expander("Model's Tool Call Request"):
                    st.json(response_message.dict())

            api_messages.append(response_message)  # Add assistant's tool request

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_tools.get(function_name)
                
                if not function_to_call:
                    st.error(f"Model tried to call an unknown function: {function_name}")
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments)
                    if verbose:
                        with st.expander(f"Executing Tool: `{function_name}`"):
                            st.write("Arguments:")
                            st.json(function_args)
                    else:
                         message_placeholder.markdown(
                            f"""{thinking_message}

Calling QuickBooks: `{function_name}({json.dumps(function_args, indent=2)})`"""
                        )
                    
                    function_response = function_to_call(**function_args)

                    if verbose:
                        with st.expander("Tool Response"):
                            st.json(function_response)
                    
                    api_messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(function_response),
                        }
                    )
                except json.JSONDecodeError:
                    st.error(f"Invalid arguments from model for {function_name}: {tool_call.function.arguments}")
                    continue
                except Exception as e:
                    st.error(f"Error executing tool {function_name}: {e}")
                    # Add error message to context for the model
                    api_messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            if verbose:
                with st.expander("Second API Call Messages (with tool results)"):
                    st.json(api_messages)

            # === Secondary API Call (with tool results) ===
            message_placeholder.markdown(thinking_message + " Summarizing...▌")
            second_response = client.chat.completions.create(
                model=os.getenv("XAI_MODEL", "grok-4"),
                messages=api_messages,
            )
            final_response = second_response.choices[0].message.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})

        # === Standard Response (no tool call) ===
        else:
            if verbose:
                with st.expander("Model's Response (no tool call)"):
                    st.json(response_message.dict())
            final_response = response_message.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})