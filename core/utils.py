import logging

logger = logging.getLogger('self_improvement_logger')

def make_api_call(client, model, messages, response_format=None):
    """Makes an API call to the specified client and model."""
    try:
        api_call_args = {
            "model": model,
            "messages": messages,
        }
        if response_format:
            api_call_args["response_format"] = response_format

        response = client.chat.completions.create(**api_call_args)
        return response.choices[0].message
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        return None
