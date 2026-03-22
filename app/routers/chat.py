from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.chat_service import chat_service
from typing import Optional

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str
    role: str = "CFO" # CFO, Founder, Sales

class ChatResponse(BaseModel):
    response: str
    role_used: str

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Process a chat message with the specified persona role.
    """
    try:
        # In a real app, we would load context per request or session. 
        # Here we assume context is pre-loaded or we mock the check.
        # For the demo, we'll let the service use its internal state or default.
        
        response_text = chat_service.process_message(request.message, request.role)
        return ChatResponse(response=response_text, role_used=request.role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
