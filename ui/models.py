from pydantic import BaseModel

class ChatRequest(BaseModel):
    model: str
    messages: list

class ChatResponse(BaseModel):
    reply: str


class FeedbackRequest(BaseModel):
    feedback_type: str  
    user_id: str
    chat_id: str
    message_idx: int