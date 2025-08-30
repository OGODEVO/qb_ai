import logging

logger = logging.getLogger('self_improvement_logger')

def make_api_call(client, **kwargs):
    """Makes an API call to the specified client and model."""
    try:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        return None
