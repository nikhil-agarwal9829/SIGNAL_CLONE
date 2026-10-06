from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from db.database import get_db
from models.user import User, Session as UserSession, Profile
from schemas.auth import PhoneRequest, VerifyOTPRequest, ProfileCreateRequest, SessionResponse
from auth_utils import generate_session_token, hash_token, get_expires_at

router = APIRouter(prefix="/api/auth", tags=["auth"])

FIXED_OTP = "123456"

@router.post("/request-otp")
def request_otp(data: PhoneRequest):
    # In a real app, send SMS here. For now, mock success.
    return {"message": f"OTP sent to {data.phone}. Use {FIXED_OTP}"}

@router.post("/verify-otp")
def verify_otp(data: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)):
    if data.otp != FIXED_OTP:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user = db.query(User).filter(User.phone == data.phone).first()
    is_new_user = False

    if not user:
        is_new_user = True
        user = User(phone=data.phone)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Auto-seed contacts and groups for the new user
        from models.user import Contact
        from models.conversation import Conversation, ConversationMember
        
        # Add all existing users as contacts (or at least the seeded ones)
        existing_users = db.query(User).filter(User.id != user.id).limit(10).all()
        for eu in existing_users:
            db.add(Contact(user_id=user.id, contact_user_id=eu.id))
            db.add(Contact(user_id=eu.id, contact_user_id=user.id)) # mutual
            
            # Create a direct conversation automatically
            conv = Conversation(type="direct", created_by=eu.id)
            db.add(conv)
            db.commit()
            db.add(ConversationMember(conversation_id=conv.id, user_id=user.id, role="admin"))
            db.add(ConversationMember(conversation_id=conv.id, user_id=eu.id, role="admin"))
        
        # Ensure a "Global Signal Group" exists and add user
        global_group = db.query(Conversation).filter(Conversation.name == "Global Signal Group", Conversation.type == "group").first()
        if not global_group:
            global_group = Conversation(type="group", name="Global Signal Group", created_by=user.id)
            db.add(global_group)
            db.commit()
        db.add(ConversationMember(conversation_id=global_group.id, user_id=user.id, role="member"))
        
        project_team = db.query(Conversation).filter(Conversation.name == "Project Team", Conversation.type == "group").first()
        if not project_team:
            project_team = Conversation(type="group", name="Project Team", created_by=user.id)
            db.add(project_team)
            db.commit()
        db.add(ConversationMember(conversation_id=project_team.id, user_id=user.id, role="member"))
            
        db.commit()

    # Create session
    token = generate_session_token()
    hashed_token = hash_token(token)
    
    db_session = UserSession(
        user_id=user.id,
        token_hash=hashed_token,
        expires_at=get_expires_at()
    )
    db.add(db_session)
    db.commit()

    # Set HTTP-only cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,  # Set True in production (HTTPS)
        samesite="none",
        max_age=30 * 24 * 60 * 60  # 30 days
    )

    return {"message": "Authenticated", "is_new_user": is_new_user}

def get_current_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    hashed_token = hash_token(session_token)
    db_session = db.query(UserSession).filter(
        UserSession.token_hash == hashed_token,
        UserSession.revoked_at == None,
        UserSession.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not db_session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
        
    user = db.query(User).filter(User.id == db_session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "display_name": profile.display_name if profile else "Unknown",
        "avatar_url": profile.avatar_url if profile else None,
        "about": profile.about if profile else None
    }

@router.post("/profile")
def set_profile(data: ProfileCreateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if profile:
        profile.display_name = data.display_name
        profile.avatar_url = data.avatar_url
        profile.about = data.about
    else:
        profile = Profile(
            user_id=current_user.id,
            display_name=data.display_name,
            avatar_url=data.avatar_url,
            about=data.about
        )
        db.add(profile)
        
    db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/logout")
def logout(response: Response, session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if session_token:
        hashed_token = hash_token(session_token)
        db_session = db.query(UserSession).filter(UserSession.token_hash == hashed_token).first()
        if db_session:
            db_session.revoked_at = datetime.now(timezone.utc)
            db.commit()
            
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully"}
