import random
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Melos Mock API")

_MELOS_CHUNKS: list[str] = []


def _load_melos() -> None:
    text = Path("melos.txt").read_text(encoding="utf-8").strip()
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 10:
            _MELOS_CHUNKS.append(line)


_load_melos()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "gpt-3.5-turbo"
    messages: list[Message] = []
    stream: bool = False


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    content = random.choice(_MELOS_CHUNKS)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": len(content), "total_tokens": 10 + len(content)},
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
