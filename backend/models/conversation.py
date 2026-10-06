from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from db.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False) # 'direct' or 'group'
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    members = relationship("ConversationMember", back_populates="conversation")
    # messages relationship defined in message.py

class ConversationMember(Base):
    __tablename__ = "conversation_members"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, default="member", nullable=False) # 'member' or 'admin'
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    left_at = Column(DateTime, nullable=True)
    # Using integer without FK to avoid circular import/creation issues with Message before ConversationMember
    last_read_message_id = Column(Integer, nullable=True) 
    unread_count = Column(Integer, default=0, nullable=False)
    muted_until = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="members")
