import os
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import User, Profile

def update_name():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == "9785836544").first()
        if user:
            profile = db.query(Profile).filter(Profile.user_id == user.id).first()
            if profile:
                profile.display_name = "Nikhil"
            else:
                profile = Profile(user_id=user.id, display_name="Nikhil", about="Available")
                db.add(profile)
            db.commit()
            print("Successfully updated name to 'Nikhil' for user 9785836544")
        else:
            print("User 9785836544 not found in database!")
    finally:
        db.close()

if __name__ == "__main__":
    update_name()
