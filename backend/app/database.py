"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import get_settings
from backend.app.models.database import Base
import logging

logger = logging.getLogger(__name__)

# Get database URL from config
settings = get_settings()
DATABASE_URL = settings.database_url

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=settings.debug,
    pool_pre_ping=True,  # Verify connections before using
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created/verified")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
