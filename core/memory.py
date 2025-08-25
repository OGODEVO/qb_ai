import os
import json
import uuid
import logging
import chromadb
from datetime import datetime

class LongTermMemory:
    def __init__(self, collection_name="long_term_memory"):
        """
        Initializes the LongTermMemory class for ChromaDB Cloud.
        """
        # Configure logging
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(log_dir, 'memory.log')
        logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - MEMORY SAVED - %(message)s')
        
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

    def save_memory(self, memory_text: str):
        """
        Saves a text string to the long-term memory.

        Args:
            memory_text (str): The text to save.
        """
        if not memory_text:
            return

        self.collection.add(
            documents=[memory_text],
            metadatas=[{"timestamp": datetime.now().isoformat()}],
            ids=[str(uuid.uuid4())]
        )
        logging.info(memory_text)

    def query_memory(self, query_text: str, n_results: int = 3) -> list[str]:
        """
        Queries the long-term memory for relevant information.

        Args:
            query_text (str): The text to query for.
            n_results (int): The number of results to return.

        Returns:
            list[str]: A list of the most relevant memories.
        """
        if not query_text:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        return results.get("documents", [[]])[0]

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
            
            if result.get("is_memorable"):
                return result.get("summary")
            
            return None

        except Exception as e:
            # Log the error or handle it as needed
            print(f"Error during memory evaluation: {e}")
            return None
