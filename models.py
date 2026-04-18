from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from database import Base

class Worksheet(Base):
    __tablename__ = "worksheets"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending", index=True) # pending, assigned, completed
    assigned_to = Column(String, index=True, nullable=True) # Phone number of assigned user
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
