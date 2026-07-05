from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


class Patient(Base):
    """Patient record with UUID-based patient_id"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    patient_id = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    profile = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    health_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    profile = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    health_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True
    )
    status = Column(
        String(50),
        nullable=False,
        server_default=text("'active'")
    )
    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)

    metadata_json = Column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb")
    )

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        Integer,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    sender = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )


class DoctorKnowledge(Base):
    __tablename__ = "doctor_knowledge"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    metadata_json = Column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb")
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
