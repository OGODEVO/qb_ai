import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal
from dotenv import load_dotenv
from fastapi_mcp import FastApiMCP

from core.agent import handle_chat_completion
from core.history import load_history, save_history

# --- Initialization ---
load_dotenv(override=True)

app = FastAPI()

@app.get("/v1/models")
async def list_models():
    """
    OpenAI-compatible models endpoint.
    """ 
    return {
        "data": [
            {
                "id": "grok-4",
                "object": "model",
                "created": 1677610602,
                "owned_by": "xai"
            }
        ],
        "object": "list"
    }

# --- OpenAI-Compatible Endpoint ---
class ChatCompletionRequest(BaseModel):
    messages: list
    model: str
    stream: bool = False

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint.
    """
    try:
        response_message = handle_chat_completion(request.messages, request.model, request.stream)
        return {
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_message.content,
                },
                "finish_reason": "stop",
            }],
            "model": request.model,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MCP Server ---
mcp = FastApiMCP(app, name="Reki", description="An agent that can answer questions about QuickBooks, Meta Ads, and Google Calendar.")
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)