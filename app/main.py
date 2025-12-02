from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models
from .schemas import ChatRequest, ChatResponse
from .game_service import process_message

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AdivinhaBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)):
    reply, finished, new_session_id = process_message(
        db=db,
        session_id=payload.session_id,
        user_message=payload.user_message,
    )

    return ChatResponse(
        session_id=new_session_id,
        reply=reply,
        finished=finished,
    )


@app.get("/")
def root():
    return {"message": "AdivinhaBot API está no ar. Use /chat para jogar."}