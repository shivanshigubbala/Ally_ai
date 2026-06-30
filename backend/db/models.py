from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    profile = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    health_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, server_default=text("'active'"))
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    metadata = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))

class DoctorKnowledge(Base):
    __tablename__ = "doctor_knowledge"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
