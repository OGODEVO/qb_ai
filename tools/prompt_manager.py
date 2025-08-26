import os

PROMPT_FILE = "prompts/system.txt"

class PromptManager:
    def __init__(self):
        """
        Initializes the PromptManager.
        """
        pass

    def get_prompt(self) -> str:
        """
        Reads the current system prompt from the prompt file.

        Returns:
            str: The current system prompt.
        """
        if not os.path.exists(PROMPT_FILE):
            return ""

        with open(PROMPT_FILE, "r") as f:
            return f.read()

    def add_to_prompt(self, text: str) -> str:
        """
        Adds a new line to the end of the prompt file.

        Args:
            text (str): The text to add to the prompt.

        Returns:
            str: A confirmation message.
        """
        with open(PROMPT_FILE, "a") as f:
            f.write("\n" + text)
        return f"Added the following to the prompt: {text}"

    def remove_from_prompt(self, text: str) -> str:
        """
        Removes a specific line from the prompt file.

        Args:
            text (str): The text to remove from the prompt.

        Returns:
            str: A confirmation message.
        """
        if not os.path.exists(PROMPT_FILE):
            return "Prompt file not found."

        with open(PROMPT_FILE, "r") as f:
            lines = f.readlines()

        with open(PROMPT_FILE, "w") as f:
            for line in lines:
                if line.strip() != text:
                    f.write(line)

        return f"Removed the following from the prompt: {text}"
