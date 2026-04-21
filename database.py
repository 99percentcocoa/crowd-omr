import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.critical("DATABASE_URL is not configured")
    raise ValueError("DATABASE_URL is not configured")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    logger.debug("Opening database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()
