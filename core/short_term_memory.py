import json
from openai import OpenAI

class ShortTermMemory:
    """
    Manages the short-term conversation history for the agent.
    """

    def __init__(self, max_history_size=20, summary_threshold=10, log_file=None):
        """
        Initializes the ShortTermMemory.

        Args:
            max_history_size (int): The maximum number of recent messages to keep.
            summary_threshold (int): The number of messages to summarize when the history grows.
            log_file (str, optional): Path to a file for logging the conversation. Defaults to None.
        """
        self.messages = []
        self.max_history_size = max_history_size
        self.summary_threshold = summary_threshold
        self.summary = ""
        self.log_file = log_file
        try:
            self.ollama_client = OpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )
        except Exception as e:
            print(f"Failed to initialize Ollama client: {e}")
            self.ollama_client = None

    def add_message(self, role: str, content: str):
        """
        Adds a message to the history and triggers summarization if needed.
        """
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_history_size:
            self.summarize_conversation()
        self.log_conversation()

    def get_history(self) -> list[dict]:
        """
        Returns the condensed conversation history.
        """
        if self.summary:
            return [{"role": "system", "content": f"This is a summary of the conversation so far: {self.summary}"}] + self.messages
        return self.messages

    def summarize_conversation(self):
        """
        Summarizes the oldest part of the conversation.
        """
        if not self.ollama_client:
            print("Cannot summarize conversation, Ollama client not available.")
            # Trim history without summarization
            self.messages = self.messages[-self.max_history_size:]
            return

        messages_to_summarize = self.messages[:-self.summary_threshold]
        if not messages_to_summarize:
            return

        prompt = "Summarize the following conversation:

"
        for msg in messages_to_summarize:
            prompt += f"{msg['role']}: {msg['content']}\n"

        try:
            response = self.ollama_client.chat.completions.create(
                model="gemma:2b",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=150,
            )
            new_summary = response.choices[0].message.content.strip()
            
            if self.summary:
                self.summary = self.summary + "\n" + new_summary
            else:
                self.summary = new_summary

            # Keep only the non-summarized part of the history
            self.messages = self.messages[-self.summary_threshold:]

        except Exception as e:
            print(f"Error during summarization: {e}")
            # If summarization fails, trim history to prevent it from growing indefinitely
            self.messages = self.messages[-self.max_history_size:]

    def log_conversation(self):
        """
        Logs the current conversation to a file.
        """
        if self.log_file:
            try:
                with open(self.log_file, "w") as f:
                    json.dump(self.messages, f, indent=2)
            except Exception as e:
                print(f"Error logging conversation: {e}")