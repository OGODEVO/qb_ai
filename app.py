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
from core.attention import AttentionLayer
from core.history import save_history, load_history
from core.memory import LongTermMemory
from tools.prompt_manager import PromptManager
from core.utils import make_api_call
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
def load_attention_layer():
    """Load the attention layer model, cached for performance."""
    return AttentionLayer(
        min_turns=int(os.getenv("ATTENTION_MIN_TURNS", 3)),
        max_turns=int(os.getenv("ATTENTION_MAX_TURNS", 8)),
        token_budget=int(os.getenv("ATTENTION_TOKEN_BUDGET", 700)),
        decay=float(os.getenv("ATTENTION_DECAY", 0.85))
    )

attention_layer = load_attention_layer()


@st.cache_resource
def load_long_term_memory():
    """Load the long-term memory store, cached for performance."""
    return LongTermMemory()

ltm = load_long_term_memory()

prompt_manager = PromptManager()

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

    verbose = st.checkbox("Verbose Mode", help="If checked, the agent will show its reasoning and tool calls.")
    st.subheader("Tools")
    use_quickbooks = st.toggle("QuickBooks", value=True)
    use_browser = st.toggle("Browser", value=True)
    use_meta_ads = st.toggle("Meta Ads", value=True)
    require_confirmation = st.checkbox("Require Confirmation", value=True, help="If checked, the agent will ask for confirmation before modifying its prompt.")

# Create a list of selected tools based on the toggle values
selected_tools = []
if use_quickbooks:
    selected_tools.append("QuickBooks")
if use_browser:
    selected_tools.append("Browser")
if use_meta_ads:
    selected_tools.append("Meta Ads")


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
BASE_SYSTEM_PROMPT = prompt_manager.get_prompt()
if not BASE_SYSTEM_PROMPT:
    st.error("System prompt file not found at 'prompts/system.txt'.")
    st.stop()

# Initialize tools
tools = []
available_tools = {}

# Add the remember_fact tool by default
tools.extend([
    {
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
    },
])
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


def proactively_save_topics_to_memory(messages: list[dict]):
    """Proactively saves summaries of recurring topics to long-term memory."""
    logger.info({"event": "proactive_memory_check_started"})
    keywords = attention_layer.extract_topics_from_history(messages)
    if not keywords:
        logger.info({"event": "proactive_memory_check_ended", "reason": "no_keywords_found"})
        return

    logger.info({"event": "proactive_memory_keywords_found", "count": len(keywords), "keywords": keywords})

    # Generate a topic name from the keywords
    topic_generation_prompt = f"Based on the following keywords and conversation snippets, generate a short, descriptive topic name for this conversation. The topic name should be a few words long and capture the main subject of the conversation.\n\nKeywords: {', '.join(keywords)}\n\nConversation Snippets:\n$" + "\n".join([msg['content'] for msg in messages])

    topic_name = make_api_call(
        client=ollama_client,
        model=os.getenv("OLLAMA_MODEL", "gemma:2b"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates concise topic names for conversations."},
            {"role": "user", "content": topic_generation_prompt},
        ],
    ).content.strip('"')

    # Check if the topic is already in memory
    retrieved_memories = ltm.query_memory(topic_name, n_results=1)
    if retrieved_memories and topic_name in retrieved_memories[0]:
        logger.info({"event": "proactive_memory_topic_skipped", "topic": topic_name, "reason": "already_in_memory"})
        return

    # Hard abort if no context is found
    relevant_messages = [msg['content'] for msg in messages if any(keyword.lower() in msg['content'].lower() for keyword in keywords)]
    if not relevant_messages:
        logger.info({"event": "proactive_memory_topic_skipped", "topic": topic_name, "reason": "no_relevant_messages"})
        return

    # Generate a summary of the topic
    summary_prompt = f"The following are messages from a conversation. Please generate a concise summary of the key information related to the topic: '{topic_name}'."
    summary_prompt += "\n\n---" + "\n\n".join(relevant_messages[:5]) # Limit to 5 messages to avoid exceeding token limit

    summary = make_api_call(
        client=ollama_client,
        model=os.getenv("OLLAMA_MODEL", "gemma:2b"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes conversation topics."},
            {"role": "user", "content": summary_prompt},
        ],
    ).content

    # Extract salient snippets as evidence
    snippet_prompt = f"""Given the following conversation snippets and a summary, extract the most salient sentences or short paragraphs that directly support the summary. Focus on key facts, decisions, or user preferences.

Summary: {summary}

Conversation Snippets:
$""" + "\n".join(relevant_messages)
    
    salient_snippets = make_api_call(
        client=ollama_client,
        model=os.getenv("OLLAMA_MODEL", "gemma:2b"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts key information from conversations."},
            {"role": "user", "content": snippet_prompt},
        ],
    ).content.split("\n")
    
    memory_to_save = {
        "topic": topic_name,
        "summary": summary,
        "evidence": salient_snippets,
        "provenance": "proactive_memory_extraction"
    }
    
    ltm.save_memory(memory_to_save)
    logger.info({"event": "proactive_memory_topic_saved", "topic": topic_name})





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

if st.session_state.waiting_for_confirmation:
    st.write("I have a new instruction for myself based on our conversation:")
    st.write(st.session_state.new_instruction)
    if st.button("Yes, add this instruction"):
        prompt_manager.add_to_prompt(st.session_state.new_instruction)
        st.session_state.waiting_for_confirmation = False
        st.session_state.new_instruction = None
        st.success("Instruction added!")
    if st.button("No, don't add this instruction"):
        st.session_state.waiting_for_confirmation = False
        st.session_state.new_instruction = None
        st.error("Instruction not added.")



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

        # Construct the system prompt with attention and LTM if available
        system_prompt = BASE_SYSTEM_PROMPT
        if retrieved_memories:
            memory_summaries = [mem.get('summary', '') for mem in retrieved_memories]
            system_prompt += "\n\n--- Relevant Memories---\n" + "\n".join(memory_summaries)
        if st.session_state.attention_suggestion:
            system_prompt += f"\n\n--- Meta-level Observation ---\n{st.session_state.attention_suggestion}"

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
            model=os.getenv("XAI_MODEL", "grok-4"),
            messages=api_messages,
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
                    
                    if verbose:
                        with st.expander("LLM's Thought Process"):
                            # thought = tool_call.function.thought
                            # if thought:
                            #     st.markdown("**Thought:**")
                            #     st.markdown(thought)

                            st.markdown(f"**Tool:** `{function_name}`")
                            
                            tool_info = next((t for t in tools if t.get("function", {}).get("name") == function_name), None)
                            if tool_info:
                                st.markdown(f"**Description:** {tool_info['function']['description']}")

                            st.markdown("**Arguments:**")
                            st.json(function_args)

                            with st.expander("Tool Code"):
                                st.code(inspect.getsource(function_to_call))
                    else:
                        message_placeholder.markdown(
                            f"""{thinking_message}

Calling tool: `{function_name}(...)`"""
                        )
                    
                    function_response = function_to_call(**function_args)

                    if verbose:
                        with st.expander("Tool Result"):
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

        # Analyze conversation for attention and memory gating
        attention_analysis = attention_layer.analyze_conversation(st.session_state.messages)
        
        if attention_analysis:
            st.session_state.attention_suggestion = attention_analysis.get("suggestion")
            similarity_score = attention_analysis.get("similarity")

            if verbose:
                with st.expander("Attention Analysis"):
                    st.write(f"Similarity Score: {similarity_score:.2f}")
                    st.markdown("**Explanation:** The similarity score measures how similar the current conversation is to past conversations that have been flagged for attention. A higher score means the current conversation is more similar to a past one.")
                    if st.session_state.attention_suggestion:
                        st.write(f"Suggestion: {st.session_state.attention_suggestion}")
                        st.markdown("**Explanation:** This suggestion is a meta-level observation about the conversation. It is generated by the attention layer to help the agent stay on track and focus on the most important aspects of the conversation.")

                    performance_report = attention_layer.get_performance_report()
                    with st.expander("Performance Report"):
                        st.json(performance_report)

                    # Check for negative messages and trigger self-correction
                    if "topics" in performance_report:
                        for topic, data in performance_report["topics"].items():
                            if data['negative'] > 0:
                                # This is where the original self_correct was called.
                                # The new background process handles this now.
                                pass

                    

            # If the conversation is coherent (i.e., a suggestion was generated), evaluate it for long-term memory
            if st.session_state.attention_suggestion:
                conversation_to_evaluate = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response},
                ]
                memory = ltm.evaluate_and_summarize_conversation(ollama_client, conversation_to_evaluate)
                if memory:
                    ltm.save_memory(memory)
                    if verbose:
                        with st.expander("Memory Saved", expanded=True):
                            st.json(memory)
        else:
            st.session_state.attention_suggestion = None

        # Proactively learn and add new stop words
        candidate_stop_words = attention_layer.identify_candidate_stop_words()
        if candidate_stop_words:
            for word in candidate_stop_words:
                attention_layer.add_custom_stop_word(word)
            st.toast(f"🧠 I've learned to ignore the following words to improve my focus: {', '.join(candidate_stop_words)}")

        # Proactively save topics to memory
        st.session_state.messages_since_last_analysis += 1
        logger.info(f"Messages since last analysis: {st.session_state.messages_since_last_analysis}")

        if st.session_state.messages_since_last_analysis >= int(os.getenv("ANALYSIS_THRESHOLD", 20)):
            messages_to_process = st.session_state.messages[-int(os.getenv("ANALYSIS_THRESHOLD", 20)):]
            proactively_save_topics_to_memory(messages_to_process)
            background_self_correction(ollama_client, ltm, messages_to_process)
            st.session_state.messages_since_last_analysis = 0
