from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://allyai:allyai@postgres:5432/allyai')
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
