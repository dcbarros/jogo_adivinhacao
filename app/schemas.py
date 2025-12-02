from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    user_message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    finished: bool