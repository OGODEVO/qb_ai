import json

class ShortTermMemory:
    """
    Manages the short-term conversation history for the agent.
    """

    def __init__(self, max_history_size=20, log_file=None):
        """
        Initializes the ShortTermMemory.

        Args:
            max_history_size (int): The maximum number of recent messages to keep.
            log_file (str, optional): Path to a file for logging the conversation. Defaults to None.
        """
        self.messages = []
        self.max_history_size = max_history_size
        self.log_file = log_file

    def add_message(self, role: str, content: str):
        """
        Adds a message to the history.
        """
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_history_size:
            self.messages.pop(0)
        self.log_conversation()

    def get_history(self) -> list[dict]:
        """
        Returns the conversation history.
        """
        return self.messages

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
