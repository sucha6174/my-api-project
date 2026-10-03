import os
import uuid
import time
import random
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api.database")

# Build connection string from environment variables
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "mydatabase")
    db_user = os.environ.get("DB_USER", "user")
    db_password = os.environ.get("DB_PASSWORD", "password")
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Standardize scheme for SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# If psycopg 3 is not directly installed, fallback to psycopg2 driver explicitly
try:
    import psycopg  # noqa: F401
except ImportError:
    if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# Configure SQLAlchemy Engine with connection pooling and timeouts
engine = create_engine(
    db_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def init_db(max_retries: int = 10, base_delay: float = 1.0, max_delay: float = 8.0) -> None:
    """
    Initializes database tables and extensions with exponential backoff and randomized
    jitter to mitigate thundering herd problems during simultaneous container startup.
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to database (attempt {attempt}/{max_retries})...")
            with engine.connect() as conn:
                try:
                    conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
                    conn.commit()
                except Exception as ext_err:
                    logger.warning(f"Note on uuid-ossp extension check: {ext_err}")

            Base.metadata.create_all(bind=engine)
            logger.info("Database schema initialized and verified successfully.")
            return
        except Exception as err:
            logger.error(f"Database connection attempt {attempt} failed: {err}")
            if attempt == max_retries:
                logger.critical("Maximum database connection retries exceeded.")
                raise err
            # Exponential backoff with jitter
            backoff = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0.1, 1.0)
            sleep_time = backoff + jitter
            logger.info(f"Retrying database connection in {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)


def get_db():
    """
    FastAPI dependency yielding a transactional database session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
