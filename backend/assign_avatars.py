import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Profile, User

def assign():
    db = SessionLocal()
    users_data = [
        {"phone": "+111", "avatar_url": "/avatars/avatar1.svg"},
        {"phone": "+222", "avatar_url": "/avatars/avatar2.svg"},
        {"phone": "+333", "avatar_url": "/avatars/avatar3.svg"},
        {"phone": "+444", "avatar_url": "/avatars/avatar4.svg"},
        {"phone": "+555", "avatar_url": "/avatars/avatar5.svg"},
        {"phone": "+666", "avatar_url": "/avatars/avatar6.svg"},
        {"phone": "+777", "avatar_url": "/avatars/avatar7.svg"},
        {"phone": "+888", "avatar_url": "/avatars/avatar8.svg"},
        {"phone": "9785836544", "avatar_url": "/avatars/avatar1.svg"}
    ]
    for d in users_data:
        u = db.query(User).filter(User.phone == d["phone"]).first()
        if u:
            p = db.query(Profile).filter(Profile.user_id == u.id).first()
            if p:
                p.avatar_url = d["avatar_url"]
    db.commit()
    db.close()

if __name__ == "__main__":
    assign()
