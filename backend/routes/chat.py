import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import agent as agent_module

router = APIRouter(prefix="/chat", tags=["chat"])


class Message(BaseModel):
    role: str    # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[Message]] = []


class ChatResponse(BaseModel):
    response: str


@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest):
    executor = agent_module.get_agent()
    history = agent_module.serialize_history(
        [m.model_dump() for m in (req.history or [])]
    )
    payload = {
        "input": req.message,
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "chat_history": history,
    }
    try:
        # Run the synchronous LangChain executor in a thread so it doesn't
        # block the FastAPI event loop (important when Playwright is in use).
        result = await asyncio.to_thread(executor.invoke, payload)
        return ChatResponse(response=result["output"])
    except RuntimeError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
