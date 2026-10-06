import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.database import SessionLocal, engine, Base
from models import User, Profile, Conversation, ConversationMember, Message, Contact

def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        users_data = [
            {"phone": "+111", "name": "Nikhil Agarwal", "about": "Available", "avatar_url": "/avatars/avatar1.svg"},
            {"phone": "+222", "name": "Alice Johnson", "about": "Hey there! I am using Signal.", "avatar_url": "/avatars/avatar2.svg"},
            {"phone": "+333", "name": "Bob Williams", "about": "Working hard", "avatar_url": "/avatars/avatar3.svg"},
            {"phone": "+444", "name": "Charlie Brown", "about": "At the gym", "avatar_url": "/avatars/avatar4.svg"},
            {"phone": "+555", "name": "David Miller", "about": "Sleeping", "avatar_url": "/avatars/avatar5.svg"},
            {"phone": "+666", "name": "Emma Wilson", "about": "In a meeting", "avatar_url": "/avatars/avatar6.svg"},
            {"phone": "+777", "name": "Rahul Sharma", "about": "Busy", "avatar_url": "/avatars/avatar7.svg"},
            {"phone": "+888", "name": "Priya Singh", "about": "Available", "avatar_url": "/avatars/avatar8.svg"},
        ]
        
        user_ids = []
        for u in users_data:
            existing = db.query(User).filter(User.phone == u["phone"]).first()
            if not existing:
                new_user = User(phone=u["phone"])
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                
                profile = Profile(user_id=new_user.id, display_name=u["name"], about=u["about"], avatar_url=u["avatar_url"])
                db.add(profile)
                db.commit()
                user_ids.append(new_user.id)
            else:
                user_ids.append(existing.id)
                
        if len(user_ids) < 8:
            return

        # Add contacts
        for i in range(len(user_ids)):
            for j in range(len(user_ids)):
                if i != j:
                    existing_contact = db.query(Contact).filter_by(user_id=user_ids[i], contact_user_id=user_ids[j]).first()
                    if not existing_contact:
                        db.add(Contact(user_id=user_ids[i], contact_user_id=user_ids[j]))
        db.commit()

        def create_direct(u1, u2):
            # Check if exists
            c = db.query(ConversationMember).filter(ConversationMember.user_id == u1).all()
            for mem in c:
                conv = db.query(Conversation).filter(Conversation.id == mem.conversation_id, Conversation.type == "direct").first()
                if conv:
                    mem2 = db.query(ConversationMember).filter(ConversationMember.conversation_id == conv.id, ConversationMember.user_id == u2).first()
                    if mem2:
                        return conv.id
            
            conv = Conversation(type="direct", created_by=u1)
            db.add(conv)
            db.commit()
            db.add(ConversationMember(conversation_id=conv.id, user_id=u1, role="admin"))
            db.add(ConversationMember(conversation_id=conv.id, user_id=u2, role="admin"))
            db.commit()
            return conv.id
            
        def create_group(name, members, created_by):
            g = db.query(Conversation).filter(Conversation.name == name, Conversation.type == "group").first()
            if not g:
                g = Conversation(type="group", name=name, created_by=created_by)
                db.add(g)
                db.commit()
                for m in members:
                    db.add(ConversationMember(conversation_id=g.id, user_id=m, role="member" if m != created_by else "admin"))
                db.commit()
            return g.id
            
        def add_msg(conv_id, sender_id, text, time_offset_minutes, read_by=None):
            m = Message(
                conversation_id=conv_id,
                sender_id=sender_id,
                content=text,
                created_at=datetime.utcnow() - timedelta(minutes=time_offset_minutes)
            )
            db.add(m)
            db.commit()
            return m
            
        # Create Directs
        nikhil = user_ids[0]
        alice = user_ids[1]
        bob = user_ids[2]
        charlie = user_ids[3]
        rahul = user_ids[6]
        priya = user_ids[7]

        c_alice = create_direct(nikhil, alice)
        c_bob = create_direct(nikhil, bob)
        c_charlie = create_direct(nikhil, charlie)
        c_rahul = create_direct(nikhil, rahul)
        c_priya = create_direct(nikhil, priya)
        
        # Create Groups
        g_global = create_group("Global Signal Group", user_ids, nikhil)
        g_project = create_group("Project Team", [nikhil, alice, bob, charlie], nikhil)
        g_friends = create_group("College Friends", [nikhil, rahul, priya, user_ids[4], user_ids[5]], nikhil)
        
        # Check if messages seeded
        if db.query(Message).count() == 0:
            # Seed Alice
            add_msg(c_alice, alice, "Hey! Are you free today?", 120)
            add_msg(c_alice, nikhil, "Yeah, what happened?", 115)
            add_msg(c_alice, alice, "I wanted to discuss the project.", 110)
            add_msg(c_alice, nikhil, "Sure. Let's talk after 6.", 105)
            add_msg(c_alice, alice, "Perfect 👍", 5) # Unread!
            
            # Seed Bob
            add_msg(c_bob, bob, "Hey Nikhil", 1440 * 2) # 2 days ago
            add_msg(c_bob, nikhil, "Hey Bob!", 1440 * 2 - 5)
            add_msg(c_bob, bob, "Did you complete the API?", 1440) # yesterday
            add_msg(c_bob, nikhil, "Almost. I'm testing it now.", 1440 - 10)
            add_msg(c_bob, bob, "Great. Let me know when it's ready.", 30) # Unread!
            
            # Seed Charlie
            add_msg(c_charlie, charlie, "Are we meeting tomorrow?", 60)
            add_msg(c_charlie, nikhil, "Yes, around 10 AM.", 50)
            add_msg(c_charlie, charlie, "Perfect.", 40)
            
            # Seed Rahul
            add_msg(c_rahul, rahul, "Did you check the assignment?", 2880)
            add_msg(c_rahul, nikhil, "Yes, I'm working on it.", 2870)
            add_msg(c_rahul, rahul, "Nice 👍", 2860)
            
            # Seed Priya
            add_msg(c_priya, priya, "Hey!", 500)
            add_msg(c_priya, nikhil, "Hey Priya", 490)
            add_msg(c_priya, priya, "Can you send me the notes?", 480)
            add_msg(c_priya, nikhil, "Sure, I'll send them tonight.", 10)
            
            # Seed Groups
            add_msg(g_project, alice, "Let's finish the API today.", 200)
            add_msg(g_project, bob, "I'll handle the backend.", 190)
            add_msg(g_project, nikhil, "I'll handle the frontend.", 180)
            
            add_msg(g_global, alice, "Welcome everyone!", 4000)
            add_msg(g_global, bob, "Hey guys 👋", 3900)
            add_msg(g_global, nikhil, "Glad to be here.", 3800)
            add_msg(g_global, charlie, "Let's get started.", 3700)
            
        print("Database seeded with realistic UI data!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
