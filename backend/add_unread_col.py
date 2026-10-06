import sqlite3
import os

db_path = os.path.join("data", "signal.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE conversation_members ADD COLUMN unread_count INTEGER DEFAULT 0')
    conn.commit()
    print("Added unread_count column")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
