from typing import Dict, List
from fastapi import WebSocket
import json
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from models.user import User

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of their active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Broadcast online status
        await self.broadcast_presence(user_id, "online")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                
                # Broadcast offline status
                await self.broadcast_presence(user_id, "offline")

    async def broadcast_presence(self, user_id: int, status: str, last_seen_at: str = None):
        msg = {
            "type": "presence",
            "user_id": user_id,
            "status": status,
            "last_seen_at": last_seen_at
        }
        # In a real app, we'd only broadcast to contacts, but here we broadcast to all active for simplicity
        for uid, conns in self.active_connections.items():
            if uid != user_id:
                for conn in conns:
                    try:
                        await conn.send_text(json.dumps(msg))
                    except:
                        pass

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

    async def broadcast_to_users(self, message: dict, user_ids: List[int]):
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()
