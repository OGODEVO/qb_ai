import os
import inspect
import json
import logging
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from tools.quickbooks import qb_query, get_tools as get_qb_tools
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query, get_tools as get_meta_ads_tools
from tools.google_calendar import get_tools as get_calendar_tools, list_events, add_event, update_event, delete_event
from core.history import save_history, load_history
from core.memory import LongTermMemory
from core.utils import make_api_call, get_current_time, get_remember_fact_tool
from core.self_correction import background_self_correction

@st.cache_resource
def get_logger():
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, 'self_improvement.log')

    logger = logging.getLogger('self_improvement_logger')
    logger.setLevel(logging.INFO)

    # To prevent duplicate handlers, we clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.FileHandler(log_file)

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "message": record.getMessage()
            }
            return json.dumps(log_record)

    formatter = JsonFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger

logger = get_logger()

# --- Initialization ---
load_dotenv(override=True)

# Page config
st.set_page_config(
    page_title="QuickBooks Financial Advisor Agent",
    page_icon="",
    layout="centered",
)

# --- Load Models and Tools ---
@st.cache_resource
def load_long_term_memory():
    """Load the long-term memory store, cached for performance."""
    return LongTermMemory()

ltm = load_long_term_memory()

# Title
st.title("Reki")

# --- Sidebar for options ---
# Create a static directory for avatars if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

with st.sidebar:
    st.header("Options")
    user_avatar_file = st.file_uploader("Your Avatar", type=["png", "jpg", "jpeg"])
    agent_avatar_file = st.file_uploader("Agent Avatar", type=["png", "jpg", "jpeg"])

    if user_avatar_file:
        with open(os.path.join("static", "user_avatar.png"), "wb") as f:
            f.write(user_avatar_file.getbuffer())
        st.session_state.user_avatar = "static/user_avatar.png"
    
    if agent_avatar_file:
        with open(os.path.join("static", "agent_avatar.png"), "wb") as f:
            f.write(agent_avatar_file.getbuffer())
        st.session_state.agent_avatar = "static/agent_avatar.png"

    user_avatar = st.session_state.get("user_avatar", "🧑‍💻")
    agent_avatar = st.session_state.get("agent_avatar", "🤖")

    st.subheader("Tools")
    use_quickbooks = st.toggle("QuickBooks", value=True)
    use_browser = st.toggle("Browser", value=True)
    use_meta_ads = st.toggle("Meta Ads", value=True)
    use_google_calendar = st.toggle("Google Calendar", value=True)

# Create a list of selected tools based on the toggle values
selected_tools = []
if use_quickbooks:
    selected_tools.append("QuickBooks")
if use_browser:
    selected_tools.append("Browser")
if use_meta_ads:
    selected_tools.append("Meta Ads")
if use_google_calendar:
    selected_tools.append("Google Calendar")


# --- OpenAI Client Setup ---
# If using a provider other than xAI, update the client initialization.
# For LiteLLM, you might use: from litellm import completion
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
    st.error(
        "Missing xAI credentials. Please set XAI_API_KEY and XAI_BASE_URL in your .env file."
    )
    st.stop()

# --- System Prompt and Tools ---
try:
    with open("prompts/system.txt", "r") as f:
        BASE_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    st.error("System prompt file not found at 'prompts/system.txt'.")
    st.stop()

# Initialize tools
tools = []
available_tools = {}

# Add the remember_fact tool by default
tools.append(get_remember_fact_tool())
available_tools["remember_fact"] = ltm.remember_fact

if "QuickBooks" in selected_tools:
    tools.extend(get_qb_tools())
    available_tools["qb_query"] = qb_query

if "Browser" in selected_tools:
    browser_tool = BrowserTool()
    tools.extend(browser_tool.get_tools())
    available_tools["browser_search"] = browser_tool.search

if "Meta Ads" in selected_tools:
    tools.extend(get_meta_ads_tools())
    available_tools["meta_ads_query"] = meta_ads_query

if "Google Calendar" in selected_tools:
    tools.extend(get_calendar_tools())
    available_tools["list_events"] = list_events
    available_tools["add_event"] = add_event
    available_tools["update_event"] = update_event
    available_tools["delete_event"] = delete_event


# --- Chat UI and Logic ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = load_history()
if "attention_suggestion" not in st.session_state:
    st.session_state.attention_suggestion = None
if "waiting_for_confirmation" not in st.session_state:
    st.session_state.waiting_for_confirmation = False
if "new_instruction" not in st.session_state:
    st.session_state.new_instruction = None

if "messages_since_last_analysis" not in st.session_state:
    st.session_state.messages_since_last_analysis = 0

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
    with st.chat_message("assistant", avatar=agent_avatar):
        message_placeholder = st.empty()
        thinking_message = "Thinking..."
        message_placeholder.markdown(thinking_message + "▌")

        # Query long-term memory
        retrieved_memories = ltm.query_memory(prompt)

        # Construct the system prompt with LTM if available
        system_prompt = BASE_SYSTEM_PROMPT.format(current_time=get_current_time())
        if retrieved_memories:
            memory_summaries = [mem.get('summary', '') for mem in retrieved_memories]
            system_prompt += "\n\n--- Relevant Memories---" + "\n".join(memory_summaries)

        # Construct messages for API call
        api_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages

        # === Primary API Call ===
        api_call_args = {
            "model": os.getenv("XAI_MODEL", "grok-4"),
            "messages": api_messages,
        }
        if tools:
            api_call_args["tools"] = tools
            api_call_args["tool_choice"] = "auto"

        response_message = make_api_call(
            client=client,
            **api_call_args,
        )
        tool_calls = response_message.tool_calls

        # === Tool-Calling Logic ===
        if tool_calls:
            api_messages.append(response_message)
            executed_tool_calls = set()

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_tools.get(function_name)
                
                if not function_to_call:
                    st.error(f"Model tried to call an unknown function: {function_name}")
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments)
                    tool_call_identifier = f"{function_name}-{json.dumps(function_args, sort_keys=True)}"

                    if tool_call_identifier in executed_tool_calls:
                        continue # Skip duplicate tool calls
                    
                    executed_tool_calls.add(tool_call_identifier)
                    
                    message_placeholder.markdown(
                        f'''{thinking_message}

Calling tool: `{function_name}(...)`'''
                    )
                    
                    function_response = function_to_call(**function_args)

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
                    api_messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps({"error": str(e)}),
                        }
                    )

            # === Secondary API Call (with tool results) ===
            message_placeholder.markdown(thinking_message + " Summarizing...▌")
            final_response_obj = make_api_call(
                client=client,
                model=os.getenv("XAI_MODEL", "grok-4"),
                messages=api_messages,
            )
            final_response = final_response_obj.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})

        # === Standard Response (no tool call) ===
        else:
            final_response = response_message.content
            message_placeholder.markdown(final_response)
            st.session_state.messages.append({"role": "assistant", "content": final_response})

        # --- Post-response Actions ---

        # Save the entire conversation history (short-term)
        save_history(st.session_state.messages)

        # Proactively save topics to memory
        st.session_state.messages_since_last_analysis += 1
        logger.info(f"Messages since last analysis: {st.session_state.messages_since_last_analysis}")

        if st.session_state.messages_since_last_analysis >= int(os.getenv("ANALYSIS_THRESHOLD", 15)):
            messages_to_process = st.session_state.messages[-int(os.getenv("ANALYSIS_THRESHOLD", 15)):]
            background_self_correction(ollama_client, ltm, messages_to_process)
            st.session_state.messages_since_last_analysis = 0
