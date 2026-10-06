from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from models.user import User, Contact, Profile
from routers.auth import get_current_user
from schemas.chat import ContactRequest, ContactResponse

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

@router.get("/", response_model=List[ContactResponse])
def get_contacts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contacts = db.query(Contact).filter(Contact.user_id == current_user.id).all()
    result = []
    for c in contacts:
        contact_user = db.query(User).filter(User.id == c.contact_user_id).first()
        profile = db.query(Profile).filter(Profile.user_id == c.contact_user_id).first()
        if contact_user and profile:
            result.append({
                "id": c.id,
                "contact_user_id": c.contact_user_id,
                "display_name": profile.display_name,
                "phone": contact_user.phone,
                "avatar_url": profile.avatar_url
            })
    return result

@router.post("/", response_model=ContactResponse)
def add_contact(data: ContactRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.phone == current_user.phone:
        raise HTTPException(status_code=400, detail="Cannot add yourself")
        
    contact_user = db.query(User).filter(User.phone == data.phone).first()
    if not contact_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    existing_contact = db.query(Contact).filter(
        Contact.user_id == current_user.id,
        Contact.contact_user_id == contact_user.id
    ).first()
    
    if existing_contact:
        raise HTTPException(status_code=400, detail="Contact already exists")
        
    new_contact = Contact(user_id=current_user.id, contact_user_id=contact_user.id)
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    profile = db.query(Profile).filter(Profile.user_id == contact_user.id).first()
    display_name = profile.display_name if profile else "Unknown"
    avatar_url = profile.avatar_url if profile else None
    
    return {
        "id": new_contact.id,
        "contact_user_id": contact_user.id,
        "display_name": display_name,
        "phone": contact_user.phone,
        "avatar_url": avatar_url
    }
