from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import engine, Base
from models import * # This ensures all models are imported before creating tables

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Signal Clone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.contacts import router as contacts_router
from routers.conversations import router as conversations_router

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(contacts_router)
app.include_router(conversations_router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Signal Clone API"}
