import os
import json
import logging
import streamlit as st
import requests
from dotenv import load_dotenv

from core.history import save_history, load_history
from core.agent import handle_chat_completion, ltm, ollama_client
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

    st.header("Manage Tool Servers")

    tool_server_url = st.text_input("openapi.json URL or Path", placeholder="http://localhost:8000/openapi.json")
    st.markdown("WebUI will make requests to \"/openapi.json\"")
    if st.button("Add Connection"):
        if tool_server_url:
            try:
                response = requests.post("http://127.0.0.1:8000/tool_servers", json={"url": tool_server_url})
                if response.status_code == 200:
                    st.success("Tool server added successfully!")
                else:
                    st.error(f"Failed to add tool server: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to the API: {e}")
        else:
            st.warning("Please enter a tool server URL.")

    st.subheader("Connected Tool Servers")
    try:
        response = requests.get("http://127.0.0.1:8000/tool_servers")
        if response.status_code == 200:
            tool_servers = response.json()
            for i, server in enumerate(tool_servers):
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.text(server['url'])
                with col2:
                    if st.button(f"Delete##{i}"):
                        try:
                            delete_response = requests.delete(f"http://127.0.0.1:8000/tool_servers/{i}")
                            if delete_response.status_code == 200:
                                st.success("Tool server removed successfully!")
                            else:
                                st.error(f"Failed to remove tool server: {delete_response.text}")
                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to connect to the API: {e}")
        else:
            st.error("Failed to fetch tool servers.")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the API: {e}")

    user_avatar = st.session_state.get("user_avatar", "🧑‍💻")
    agent_avatar = st.session_state.get("agent_avatar", "🤖")

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

        try:
            short_term_memory = ShortTermMemory()
            for message in st.session_state.messages:
                short_term_memory.add_message(message["role"], message["content"])

            response_message = handle_chat_completion(
                short_term_memory,
                os.getenv("XAI_MODEL", "grok-4")
            )
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

        except Exception as e:
            st.error(f"An error occurred: {e}")