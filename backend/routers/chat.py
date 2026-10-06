from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import json
from datetime import datetime, timezone
from typing import Optional

from db.database import SessionLocal
from models.user import User, Session as UserSession
from models.conversation import ConversationMember
from models.message import Message
from ws_manager import manager
from auth_utils import hash_token

router = APIRouter(tags=["chat"])

async def get_ws_user(websocket: WebSocket) -> Optional[User]:
    session_token = websocket.cookies.get("session_token")
    if not session_token:
        return None
    
    hashed_token = hash_token(session_token)
    db = SessionLocal()
    try:
        db_session = db.query(UserSession).filter(
            UserSession.token_hash == hashed_token,
            UserSession.revoked_at == None,
            UserSession.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if not db_session:
            return None
            
        user = db.query(User).filter(User.id == db_session.user_id).first()
        return user
    finally:
        db.close()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    user = await get_ws_user(websocket)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user.id)
    
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.id == user.id).first()
        db_user.last_seen_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()

    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            await handle_ws_event(event, user.id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db_user.last_seen_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()

async def handle_ws_event(event: dict, user_id: int):
    event_type = event.get("type")
    
    if event_type == "message":
        db = SessionLocal()
        try:
            conversation_id = event.get("conversation_id")
            content = event.get("content")
            
            member = db.query(ConversationMember).filter(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
                ConversationMember.left_at == None
            ).first()
            
            if not member:
                return
                
            new_message = Message(
                conversation_id=conversation_id,
                sender_id=user_id,
                content=content,
                message_type="text"
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            
            members = db.query(ConversationMember).filter(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at == None
            ).all()
            
            for m in members:
                if m.user_id != user_id:
                    m.unread_count += 1
            db.commit()
            
            recipient_ids = [m.user_id for m in members]
            
            payload = {
                "type": "new_message",
                "message": {
                    "id": new_message.id,
                    "conversation_id": conversation_id,
                    "sender_id": user_id,
                    "content": content,
                    "created_at": new_message.created_at.isoformat()
                }
            }
            await manager.broadcast_to_users(payload, recipient_ids)
            
        finally:
            db.close()
            
    elif event_type == "typing":
        db = SessionLocal()
        try:
            conversation_id = event.get("conversation_id")
            members = db.query(ConversationMember).filter(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at == None
            ).all()
            
            recipient_ids = [m.user_id for m in members if m.user_id != user_id]
            
            payload = {
                "type": "typing",
                "conversation_id": conversation_id,
                "user_id": user_id
            }
            await manager.broadcast_to_users(payload, recipient_ids)
        finally:
            db.close()
