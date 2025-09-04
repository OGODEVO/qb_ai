import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi_mcp import FastApiMCP

from core.agent import handle_chat_completion
from core.short_term_memory import ShortTermMemory
from core.tool_server import get_tool_servers, add_tool_server, remove_tool_server

# --- Initialization ---
load_dotenv(override=True)
app = FastAPI()

@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
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
    stream: bool = True

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    try:
        short_term_memory = ShortTermMemory(log_file="conversation_log.json")

        # Populate short-term memory from the request
        for message in request.messages:
            short_term_memory.add_message(message["role"], message["content"])

        if request.stream:
            async def stream_generator():
                async for chunk in handle_chat_completion(short_term_memory, request.model, request.stream):
                    if chunk.choices[0].delta.content:
                        data = {
                            "choices": [{"delta": {"content": chunk.choices[0].delta.content}}],
                            "model": request.model
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(stream_generator(), media_type="text/event-stream")

        else:
            response_generator = handle_chat_completion(short_term_memory, request.model, request.stream)
            response = await anext(response_generator, None)

            if not response:
                 raise HTTPException(status_code=500, detail="Agent did not produce a response.")

            content = response.choices[0].message.content if response.choices else ""

            if content:
                short_term_memory.add_message("assistant", content)

            return {
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "model": request.model,
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Tool Server Management ---
class ToolServerRequest(BaseModel):
    url: str

@app.get("/tool_servers")
async def list_tool_servers():
    return get_tool_servers()

@app.post("/tool_servers")
async def add_tool_server_endpoint(request: ToolServerRequest):
    try:
        add_tool_server(request.url)
        return {"message": "Tool server added successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/tool_servers/{server_index}")
async def remove_tool_server_endpoint(server_index: int):
    remove_tool_server(server_index)
    return {"message": "Tool server removed successfully."}

# --- MCP Server ---
mcp = FastApiMCP(app, name="Reki", description="An agent that can answer questions about QuickBooks, Meta Ads, and Google Calendar.")
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)