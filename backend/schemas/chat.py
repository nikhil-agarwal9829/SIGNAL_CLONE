from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ContactRequest(BaseModel):
    phone: str

class ContactResponse(BaseModel):
    id: int
    contact_user_id: int
    display_name: str
    phone: str
    avatar_url: Optional[str]

    class Config:
        from_attributes = True

class ConversationCreateDirect(BaseModel):
    contact_user_id: int

class ConversationCreateGroup(BaseModel):
    name: str
    member_ids: List[int]

class ConversationMemberSchema(BaseModel):
    user_id: int
    role: str
    display_name: str
    avatar_url: Optional[str]

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    type: str
    name: Optional[str]
    avatar_url: Optional[str]
    members: List[ConversationMemberSchema]
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: Optional[str]
    message_type: str
    created_at: datetime

    class Config:
        from_attributes = True
