import os
import json
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from tools.quickbooks import qb_query
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query
from core.attention import AttentionLayer
from core.history import save_history, load_history
from core.memory import LongTermMemory

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
        min_turns=3,
        max_turns=8,
        token_budget=700,
        decay=0.85
    )

attention_layer = load_attention_layer()


@st.cache_resource
def load_long_term_memory():
    """Load the long-term memory store, cached for performance."""
    return LongTermMemory()

ltm = load_long_term_memory()


# Title
st.title("Reki")

# --- Sidebar for options ---
with st.sidebar:
    st.header("Options")
    verbose = st.checkbox("Verbose Mode", help="If checked, the agent will show its reasoning and tool calls.")
    st.subheader("Tools")
    use_quickbooks = st.toggle("QuickBooks", value=True)
    use_browser = st.toggle("Browser", value=True)
    use_meta_ads = st.toggle("Meta Ads", value=True)

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

if "QuickBooks" in selected_tools:
    tools.append(
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
    )
    available_tools["qb_query"] = qb_query

if "Browser" in selected_tools:
    browser_tool = BrowserTool()
    tools.extend(browser_tool.get_tools())
    available_tools["browser_search"] = browser_tool.search

if "Meta Ads" in selected_tools:
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "meta_ads_query",
                "description": "Query Meta Ads for advertising data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["ad", "adset", "campaign", "account"],
                            "description": "The level to aggregate results at."
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
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "A list of fields to retrieve."
                        },
                        "filters": {
                            "type": "object",
                            "properties": {
                                "campaign_id": {"type": "string"},
                                "ad_set_id": {"type": "string"},
                                "ad_id": {"type": "string"},
                            },
                            "description": "Optional filters to apply to the query."
                        }
                    },
                    "required": ["level", "start_date", "end_date", "fields"],
                },
            },
        }
    )
    available_tools["meta_ads_query"] = meta_ads_query


# --- Chat UI and Logic ---

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = load_history()
if "attention_suggestion" not in st.session_state:
    st.session_state.attention_suggestion = None

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

        # Query long-term memory
        retrieved_memories = ltm.query_memory(prompt)

        # Construct the system prompt with attention and LTM if available
        system_prompt = BASE_SYSTEM_PROMPT
        if retrieved_memories:
            system_prompt += "\n\n--- Relevant Memories ---\n" + "\n".join(retrieved_memories)
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

        response = client.chat.completions.create(**api_call_args)
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # === Tool-Calling Logic ===
        if tool_calls:
            api_messages.append(response_message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_tools.get(function_name)
                
                if not function_to_call:
                    st.error(f"Model tried to call an unknown function: {function_name}")
                    continue

                try:
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if verbose:
                        with st.expander("LLM's Thought Process"):
                            st.markdown(f"**Tool:** `{function_name}`")
                            st.markdown("**Arguments:**")
                            st.json(function_args)
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
            second_response = client.chat.completions.create(
                model=os.getenv("XAI_MODEL", "grok-4"),
                messages=api_messages,
            )
            final_response = second_response.choices[0].message.content
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
                    if st.session_state.attention_suggestion:
                        st.write(f"Suggestion: {st.session_state.attention_suggestion}")

            # If the conversation is coherent (i.e., a suggestion was generated), evaluate it for long-term memory
            if st.session_state.attention_suggestion:
                conversation_to_evaluate = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response},
                ]
                summary = ltm.evaluate_and_summarize_conversation(client, conversation_to_evaluate)
                if summary:
                    ltm.save_memory(summary)
                    if verbose:
                        with st.expander("Memory Saved", expanded=True):
                            st.write(summary)
        else:
            st.session_state.attention_suggestion = None
