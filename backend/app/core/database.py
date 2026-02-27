from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from app.core.config import settings

Base = declarative_base()

class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger)
    file_type = Column(String(50))
    table_count = Column(Integer, default=0)
    record_count = Column(Integer, default=0)
    analysis_result = Column(JSON)
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)

class TableData(Base):
    __tablename__ = "table_data"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = Column(String(36), nullable=False)
    table_name = Column(String(255), nullable=False)
    columns = Column(JSON)
    data = Column(JSON)
    row_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
