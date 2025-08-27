import os
import json
import uuid
import logging
import chromadb
from datetime import datetime

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, 'memory.log')

# Create a logger
logger = logging.getLogger('memory_logger')
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

class LongTermMemory:
    def __init__(self, collection_name="long_term_memory"):
        """
        Initializes the LongTermMemory class for ChromaDB Cloud.
        """
        try:
            api_key = os.environ["CHROMA_API_KEY"]
            tenant = os.environ["CHROMA_TENANT"]
            database = os.environ["CHROMA_DATABASE"]
        except KeyError:
            raise ConnectionError(
                "ChromaDB Cloud credentials not found. Please set CHROMA_API_KEY, "
                "CHROMA_TENANT, and CHROMA_DATABASE in your environment variables."
            )

        self.client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def save_memory(self, memory: dict):
        """
        Saves a memory to the long-term memory.

        Args:
            memory (dict): The memory to save.
        """
        if not memory:
            return

        document = memory.get("summary", "")

        # Truncate evidence to avoid ChromaDB quota errors
        evidence = memory.get("evidence", [])
        truncated_evidence = []
        MAX_EVIDENCE_SIZE = 4000  # Leave some buffer for other metadata

        for snippet in evidence:
            # Truncate individual snippet if it's too long
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."
            
            # Check if adding the new snippet exceeds the total size limit
            if len(json.dumps(truncated_evidence + [snippet])) > MAX_EVIDENCE_SIZE:
                break # Stop adding snippets if we're approaching the limit
            
            truncated_evidence.append(snippet)

        metadata = {
            "topic": memory.get("topic"),
            "provenance": memory.get("provenance"),
            "evidence": json.dumps(truncated_evidence)
        }

        self.collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )
        logger.info({"event": "memory_saved", "topic": memory.get("topic")})

    def remember_fact(self, fact: str):
        """
        Saves a specific fact to the long-term memory, intended for direct tool use.

        Args:
            fact (str): The specific fact or piece of information to remember.
        """
        if not fact:
            return

        self.collection.add(
            documents=[fact],
            metadatas=[{"timestamp": datetime.now().isoformat(), "type": "fact"}],
            ids=[str(uuid.uuid4())]
        )
        logger.info({"event": "fact_saved", "fact": fact})

    def query_memory(self, query_text: str, n_results: int = 3) -> list[dict]:
        """
        Queries the long-term memory for relevant information.

        Args:
            query_text (str): The text to query for.
            n_results (int): The number of results to return.

        Returns:
            list[dict]: A list of the most relevant memories.
        """
        if not query_text:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas"]
        )
        
        memories = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i]
                memory = {
                    "summary": doc,
                    "topic": metadata.get("topic"),
                    "provenance": metadata.get("provenance"),
                    "evidence": json.loads(metadata.get("evidence", "[]"))
                }
                memories.append(memory)
        return memories

    def evaluate_and_summarize_conversation(self, client, conversation: list[dict]) -> str | None:
        """
        Evaluates if a conversation is memorable and returns a summary if it is.

        Args:
            client: The OpenAI client instance.
            conversation (list[dict]): The recent conversation turns.

        Returns:
            str | None: A summary of the conversation if it's memorable, otherwise None.
        """
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])

        system_prompt = '''
You are a "Memory Analyst" AI. Your task is to evaluate a conversation and decide if it contains information worth saving to a long-term vector database.

Analyze the following conversation and determine if it contains significant information. Significant information includes:
- User preferences, goals, or direct instructions.
- Key facts, decisions, or solutions.
- Important details about projects, people, or plans.

Trivial exchanges, such as greetings, simple confirmations, or conversations that are unlikely to be relevant in the future, should be ignored.

Your output MUST be a JSON object with two keys:
1. "is_memorable": a boolean value (true or false).
2. "summary": a concise summary of the key information if it is memorable, or an empty string if it is not.

Example 1:
Conversation:
user: Hi there!
assistant: Hello! How can I help you today?
Output:
{"is_memorable": false, "summary": ""}

Example 2:
Conversation:
user: Please remember that my favorite color is blue.
assistant: I will remember that your favorite color is blue.
Output:
{"is_memorable": true, "summary": "The user's favorite color is blue."}

Example 3:
Conversation:
user: Can you find the latest sales report for Q2?
assistant: I've found the Q2 sales report. It shows a 15% increase in revenue.
user: Great, thanks!
Output:
{"is_memorable": true, "summary": "The Q2 sales report showed a 15% increase in revenue."}
'''

        try:
            response = client.chat.completions.create(
                model=os.getenv("XAI_MODEL", "grok-4"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info({"event": "memory_evaluation", "result": result})
            
            if result.get("is_memorable"):
                return {
                    "summary": result.get("summary"),
                    "provenance": "conversation_summary",
                    "evidence": [msg['content'] for msg in conversation]
                }
            
            return None

        except Exception as e:
            # Log the error or handle it as needed
            logger.error(f"Error during memory evaluation: {e}")
            return None
