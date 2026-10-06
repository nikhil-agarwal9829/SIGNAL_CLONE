from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List

from db.database import get_db
from models.user import User, Profile
from models.conversation import Conversation, ConversationMember
from models.message import Message
from routers.auth import get_current_user
from schemas.chat import ConversationCreateDirect, ConversationCreateGroup, ConversationResponse, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

def _build_conversation_response(db: Session, conv: Conversation, current_user_id: int):
    members = db.query(ConversationMember).filter(ConversationMember.conversation_id == conv.id, ConversationMember.left_at == None).all()
    member_schemas = []
    
    name = conv.name
    avatar = conv.avatar_url
    
    for m in members:
        profile = db.query(Profile).filter(Profile.user_id == m.user_id).first()
        member_schemas.append({
            "user_id": m.user_id,
            "role": m.role,
            "display_name": profile.display_name if profile else "Unknown",
            "avatar_url": profile.avatar_url if profile else None
        })
        
        # If direct conversation, name and avatar are based on the OTHER person
        if conv.type == "direct" and m.user_id != current_user_id:
            name = profile.display_name if profile else "Unknown"
            avatar = profile.avatar_url if profile else None

    last_msg = db.query(Message).filter(Message.conversation_id == conv.id).order_by(Message.created_at.desc()).first()
    
    current_user_member = db.query(ConversationMember).filter(ConversationMember.conversation_id == conv.id, ConversationMember.user_id == current_user_id).first()
    
    return {
        "id": conv.id,
        "type": conv.type,
        "name": name,
        "avatar_url": avatar,
        "members": member_schemas,
        "last_message": last_msg.content if last_msg else None,
        "last_message_at": last_msg.created_at if last_msg else None,
        "unread_count": current_user_member.unread_count if current_user_member else 0
    }

@router.get("/", response_model=List[ConversationResponse])
def get_conversations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_memberships = db.query(ConversationMember).filter(
        ConversationMember.user_id == current_user.id,
        ConversationMember.left_at == None
    ).all()
    
    conv_ids = [m.conversation_id for m in user_memberships]
    conversations = db.query(Conversation).filter(Conversation.id.in_(conv_ids)).all()
    
    result = []
    for conv in conversations:
        result.append(_build_conversation_response(db, conv, current_user.id))
        
    return result

@router.post("/direct", response_model=ConversationResponse)
def create_direct_conversation(data: ConversationCreateDirect, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.contact_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot create conversation with yourself")
        
    # Check if direct conversation already exists
    # Find all direct convos for current user
    user_convos = db.query(ConversationMember.conversation_id).filter(
        ConversationMember.user_id == current_user.id
    ).subquery()
    
    existing_conv = db.query(Conversation).join(ConversationMember).filter(
        Conversation.type == "direct",
        Conversation.id.in_(user_convos),
        ConversationMember.user_id == data.contact_user_id
    ).first()
    
    if existing_conv:
        return _build_conversation_response(db, existing_conv, current_user.id)
        
    # Create new
    conv = Conversation(type="direct", created_by=current_user.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    
    member1 = ConversationMember(conversation_id=conv.id, user_id=current_user.id, role="admin")
    member2 = ConversationMember(conversation_id=conv.id, user_id=data.contact_user_id, role="admin")
    
    db.add_all([member1, member2])
    db.commit()
    
    return _build_conversation_response(db, conv, current_user.id)

@router.post("/group", response_model=ConversationResponse)
def create_group_conversation(data: ConversationCreateGroup, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = Conversation(type="group", name=data.name, created_by=current_user.id)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    
    members = [ConversationMember(conversation_id=conv.id, user_id=current_user.id, role="admin")]
    for uid in data.member_ids:
        if uid != current_user.id:
            members.append(ConversationMember(conversation_id=conv.id, user_id=uid, role="member"))
            
    db.add_all(members)
    db.commit()
    
    return _build_conversation_response(db, conv, current_user.id)

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_messages(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verify membership
    member = db.query(ConversationMember).filter(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id == current_user.id,
        ConversationMember.left_at == None
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this conversation")
        
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()
    return messages

@router.post("/{conversation_id}/read")
def mark_as_read(conversation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    member = db.query(ConversationMember).filter(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id == current_user.id
    ).first()
    
    if member:
        member.unread_count = 0
        db.commit()
    return {"message": "marked as read"}
