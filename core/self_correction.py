import os
import json
import logging
from core.utils import make_api_call

logger = logging.getLogger('self_improvement_logger')

def analyze_for_corrections(ollama_client, messages: list[dict]) -> list[dict]:
    """Analyzes a batch of messages for user corrections."""
    logger.info({"event": "analyzing_for_corrections", "message_count": len(messages)})
    
    conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

    system_prompt = """
You are an AI assistant that analyzes conversations. Your task is to identify instances where the user has corrected the AI. 
A correction is when the user explicitly or implicitly points out a mistake in the AI's previous response. 
For each correction you find, provide the AI's incorrect statement and the user's suggested correction.

Your output MUST be a JSON object with a single key, "corrections", which is a list of objects. 
Each object in the list should have two keys: "incorrect_statement" and "suggested_correction".

If the user does not provide a specific correction, you should still identify the incorrect statement, but you should return `null` for the `suggested_correction`.

If no corrections are found, return an empty list.

Example 1:
Conversation:
user: What was our revenue last month?
assistant: Your revenue last month was $10,000.
user: No, it was $12,000.
Output:
{
    "corrections": [
        {
            "incorrect_statement": "Your revenue last month was $10,000.",
            "suggested_correction": "The revenue last month was $12,000."
        }
    ]
}

Example 2:
Conversation:
user: I don't think that's right.
assistant: I apologize for the error. Can you please provide the correct information?
user: The correct answer is 42.
Output:
{
    "corrections": [
        {
            "incorrect_statement": "I apologize for the error.",
            "suggested_correction": "The correct answer is 42."
        }
    ]
}

Example 3:
Conversation:
user: That's not what I asked for.
assistant: I see. My apologies. How can I better assist you?
user: I wanted a summary of the document, not the full text.
Output:
{
    "corrections": [
        {
            "incorrect_statement": "[The full text of the document]",
            "suggested_correction": "I wanted a summary of the document."
        }
    ]
}

Example 4:
Conversation:
user: That's wrong.
assistant: I see. Please provide me with the correct information.
Output:
{
    "corrections": [
        {
            "incorrect_statement": "That's wrong.",
            "suggested_correction": null
        }
    ]
}
"""

    response_content = make_api_call(
        client=ollama_client,
        model="gemma:2b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text},
        ],
        response_format={"type": "json_object"},
    )

    if response_content:
        result = json.loads(response_content)
        corrections = result.get("corrections", [])
        
        if corrections:
            logger.info({"event": "corrections_found", "count": len(corrections), "corrections": corrections})
        else:
            logger.info({"event": "no_corrections_found"})
            
        return corrections
    
    return []

def background_self_correction(ollama_client, ltm, messages: list[dict]):
    """Analyzes messages for corrections and saves them to long-term memory."""
    corrections = analyze_for_corrections(ollama_client, messages)
    for correction in corrections:
        incorrect_statement = correction["incorrect_statement"]
        suggested_correction = correction.get("suggested_correction")
        
        summary = f"The user dislikes when the agent says '{incorrect_statement}'."
        if suggested_correction:
            summary += f" The user prefers '{suggested_correction}'."

        memory = {
            "topic": "User Correction",
            "summary": summary,
            "evidence": [incorrect_statement, suggested_correction],
            "provenance": "background_self_correction"
        }
        
        ltm.save_memory(memory)
        logger.info({"event": "correction_saved_to_memory", "correction": correction})
