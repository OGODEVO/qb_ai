import os
import inspect
import json
import logging
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from tools.quickbooks import qb_query
from tools.browser import BrowserTool
from tools.meta_ads import meta_ads_query
from core.attention import AttentionLayer
from core.history import save_history, load_history
from core.memory import LongTermMemory
from tools.prompt_manager import PromptManager

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'self_improvement.log')

# Create a logger
logger = logging.getLogger('self_improvement_logger')
logger.setLevel(logging.INFO)

# Create a file handler
handler = logging.FileHandler(log_file)

# Create a JSON formatter
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

# Add the handler to the logger
logger.addHandler(handler)

def self_correct(messages):
    """Placeholder for self-correction logic."""
    print("Self-correction triggered.")

    # Create a prompt to identify the user's correction
    correction_prompt = "The following is a conversation between a user and an AI agent. The user has expressed negative sentiment, so the agent is trying to self-correct. Please identify the incorrect statement in the agent's response and the user's suggested correction. Your output should be a JSON object with two keys: 'incorrect_statement' and 'suggested_correction'."

    # Add the conversation history to the prompt
    for msg in messages:
        correction_prompt += f"\n{msg['role']}: {msg['content']}"

    # Use a language model to identify the correction
    response = client.chat.completions.create(
        model=os.getenv("XAI_MODEL", "grok-4"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that identifies user corrections in a conversation."},
            {"role": "user", "content": correction_prompt},
        ],
        response_format={"type": "json_object"},
    )

    correction = json.loads(response.choices[0].message.content)
    incorrect_statement = correction.get("incorrect_statement")
    suggested_correction = correction.get("suggested_correction")

    # Generate a new instruction based on the correction
    instruction_generation_prompt = f"The user has corrected the agent. The incorrect statement was: '{incorrect_statement}'. The user's suggested correction is: '{suggested_correction}'. Please generate a new instruction for the agent that will help it avoid making the same mistake in the future. The instruction should be a single sentence that starts with 'When...' or 'If...'."

    response = client.chat.completions.create(
        model=os.getenv("XAI_MODEL", "grok-4"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates instructions for AI agents."},
            {"role": "user", "content": instruction_generation_prompt},
        ],
    )

    new_instruction = response.choices[0].message.content
    print(f"New instruction: {new_instruction}")

    # Ask for user confirmation if required
    if require_confirmation:
        st.session_state.waiting_for_confirmation = True
        st.session_state.new_instruction = new_instruction
    else:
        prompt_manager.add_to_prompt(new_instruction)
        st.success("Instruction added!")


def proactive_improvement(topic):
    """Placeholder for proactive improvement logic."""
    print(f"Proactive improvement triggered for topic: {topic}")

    # Generate a learning plan
    learning_plan_prompt = f"I am an AI agent and I have identified that I am underperforming on the topic of {topic}. Please generate a learning plan for me to improve my understanding of this topic. The learning plan should be a series of steps that I can take to improve my knowledge and skills on this topic. The steps should be actionable and specific. For example, instead of saying 'Read a book on {topic}', you should say 'Search for and read the top 3 articles on {topic}'."

    response = client.chat.completions.create(
        model=os.getenv("XAI_MODEL", "grok-4"),
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates learning plans."},
            {"role": "user", "content": learning_plan_prompt},
        ],
    )

    learning_plan = response.choices[0].message.content
    logger.info({"event": "learning_plan_generated", "plan": learning_plan})
    st.session_state.learning_plan = learning_plan.split("\n")
    st.session_state.learning_plan_step = 0

    # Ask for user feedback on the learning plan if required
    if require_confirmation:
        st.session_state.waiting_for_learning_plan_feedback = True
    else:
        execute_learning_plan_step()
    st.info(f"🧠 Proactive improvement: Generated a learning plan for the topic '{topic}'.")

def execute_learning_plan_step():
    """Executes the current step in the learning plan."""
    if st.session_state.learning_plan and st.session_state.learning_plan_step < len(st.session_state.learning_plan):
        step = st.session_state.learning_plan[st.session_state.learning_plan_step]
        logger.info({"event": "executing_learning_plan_step", "step": step})
        st.session_state.learning_plan_step += 1

        # Use a language model to select the appropriate tool to execute the step
        tool_selection_prompt = f"I am an AI agent and I am currently executing a learning plan. The current step is: '{step}'. Please select the appropriate tool to execute this step. Your output should be a JSON object with two keys: 'tool' and 'query'. The 'tool' key should be the name of the tool to use, and the 'query' key should be the query to pass to the tool. For example, if the step is 'Search the web for articles on financial forecasting', your output should be: {{'tool': 'browser_search', 'query': 'financial forecasting'}}."

        try:
            response = client.chat.completions.create(
                model=os.getenv("XAI_MODEL", "grok-4"),
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that selects tools to execute learning plan steps."},
                    {"role": "user", "content": tool_selection_prompt},
                ],
                response_format={"type": "json_object"},
            )

            tool_selection = json.loads(response.choices[0].message.content)
            logger.info({"event": "tool_selected_for_learning_step", "tool_selection": tool_selection})
            tool_to_use = tool_selection.get("tool")
            query = tool_selection.get("query")

            # Execute the selected tool
            if tool_to_use in available_tools:
                function_to_call = available_tools[tool_to_use]
                function_response = function_to_call(query)
                logger.info({"event": "tool_executed_for_learning_step", "tool": tool_to_use, "response": function_response})
            else:
                logger.error({"event": "unknown_tool_for_learning_step", "tool": tool_to_use})
        except Exception as e:
            logger.error({"event": "error_executing_learning_plan_step", "error": str(e)})


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
    {
        "type": "function",
        "function": {
            "name": "add_to_prompt",
            "description": "Adds a new line to the end of the agent's system prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to add to the prompt."
                    }
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_prompt",
            "description": "Removes a specific line from the agent's system prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to remove from the prompt."
                    }
                },
                "required": ["text"],
            },
        },
    },
])
available_tools["remember_fact"] = ltm.remember_fact
available_tools["add_to_prompt"] = prompt_manager.add_to_prompt
available_tools["remove_from_prompt"] = prompt_manager.remove_from_prompt

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


def proactively_save_topics_to_memory(messages: list[dict]):
    """Proactively saves summaries of recurring topics to long-term memory."""
    logger.info({"event": "proactive_memory_check_started"})
    topics = attention_layer.extract_topics_from_history(messages)
    if not topics:
        logger.info({"event": "proactive_memory_check_ended", "reason": "no_topics_found"})
        return

    logger.info({"event": "proactive_memory_topics_found", "topics": topics})

    for topic in topics:
        # Check if the topic is already in memory
        retrieved_memories = ltm.query_memory(topic, n_results=1)
        if retrieved_memories and topic in retrieved_memories[0]:
            logger.info({"event": "proactive_memory_topic_skipped", "topic": topic, "reason": "already_in_memory"})
            continue

        # Hard abort if no context is found
        relevant_messages = [msg['content'] for msg in messages if topic in msg['content']]
        if not relevant_messages:
            logger.info({"event": "proactive_memory_topic_skipped", "topic": topic, "reason": "no_relevant_messages"})
            continue

        # Generate a summary of the topic
        summary_prompt = f"The following are messages from a conversation. Please generate a concise summary of the key information related to the topic: '{topic}'."
        summary_prompt += "\n\n---\n\n".join(relevant_messages[:5]) # Limit to 5 messages to avoid exceeding token limit

        response = client.chat.completions.create(
            model=os.getenv("XAI_MODEL", "grok-4"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversation topics."},
                {"role": "user", "content": summary_prompt},
            ],
        )
        summary = response.choices[0].message.content

        # Extract salient snippets as evidence
        snippet_prompt = f"Given the following conversation snippets and a summary, extract the most salient sentences or short paragraphs that directly support the summary. Focus on key facts, decisions, or user preferences. 

Summary: {summary}

Conversation Snippets:
" + "\n".join(relevant_messages)
        
        snippet_response = client.chat.completions.create(
            model=os.getenv("XAI_MODEL", "grok-4"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts key information from conversations."},
                {"role": "user", "content": snippet_prompt},
            ],
        )
        salient_snippets = snippet_response.choices[0].message.content.split("\n")
        
        memory_to_save = {
            "topic": topic,
            "summary": summary,
            "evidence": salient_snippets,
            "provenance": "proactive_memory_extraction"
        }
        
        ltm.save_memory(memory_to_save)
        logger.info({"event": "proactive_memory_topic_saved", "memory": memory_to_save})


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
if "learning_plan" not in st.session_state:
    st.session_state.learning_plan = None
if "learning_plan_step" not in st.session_state:
    st.session_state.learning_plan_step = 0
if "waiting_for_learning_plan_feedback" not in st.session_state:
    st.session_state.waiting_for_learning_plan_feedback = False

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

if st.session_state.learning_plan and not st.session_state.waiting_for_learning_plan_feedback:
    st.write("I am currently working on the following learning plan:")
    st.write(st.session_state.learning_plan)
    st.write(f"Current step: {st.session_state.learning_plan[st.session_state.learning_plan_step]}")

if st.session_state.waiting_for_learning_plan_feedback:
    st.write("I have generated a learning plan for myself. Please review it and let me know if you would like me to proceed.")
    st.write(st.session_state.learning_plan)
    if st.button("Yes, proceed with the learning plan"):
        st.session_state.waiting_for_learning_plan_feedback = False
        execute_learning_plan_step()
        st.success("Learning plan approved!")
    if st.button("No, do not proceed with the learning plan"):
        st.session_state.waiting_for_learning_plan_feedback = False
        st.session_state.learning_plan = None
        st.session_state.learning_plan_step = 0
        st.error("Learning plan rejected.")

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

        response = client.chat.completions.create(**api_call_args)
        response_message = response.choices[0].message
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
                                self_correct(st.session_state.messages)
                                break # Trigger only once per turn

                    underperforming_topics = attention_layer.get_underperforming_topics()
                    if underperforming_topics:
                        for topic in underperforming_topics:
                            proactive_improvement(topic)

            # If the conversation is coherent (i.e., a suggestion was generated), evaluate it for long-term memory
            if st.session_state.attention_suggestion:
                conversation_to_evaluate = [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": final_response},
                ]
                memory = ltm.evaluate_and_summarize_conversation(client, conversation_to_evaluate)
                if memory:
                    ltm.save_memory(memory)
                    if verbose:
                        with st.expander("Memory Saved", expanded=True):
                            st.json(memory)
        else:
            st.session_state.attention_suggestion = None

        # Proactively save topics to memory
        proactively_save_topics_to_memory(st.session_state.messages)