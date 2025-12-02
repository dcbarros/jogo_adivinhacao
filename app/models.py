from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from .database import Base

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    category = Column(String, nullable=False)
    word = Column(String, nullable=False)
    hints_json = Column(Text, nullable=False)
    attempts = Column(Integer, default=0)
    finished = Column(Boolean, default=False)
    create_at = Column(DateTime, default=datetime.now(timezone.utc))