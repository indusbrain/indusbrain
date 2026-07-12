import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv  # ◄── [NEW IMPORT ADDED]

# ◄── [CRITICAL ENTRY]: Scan disk and pull .env strings into live active memory
load_dotenv()

# Fetch our secret connection keys safely from environment memory
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure our initialization fails fast with an explainable message if keys are missing
if not DATABASE_URL:
    raise ValueError("🚨 CRITICAL ERROR: DATABASE_URL variable is entirely missing from memory context!")

# Instantiate the asynchronous engine engine pool blueprint
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20
)

# ... (Keep the rest of your sessionmaker, Base, and get_db function code exactly the same below)

# 3. Create a session maker template factory that generates individual connection tickets
async_session_local = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False   # Prevents SQLAlchemy from breaking objects after a save
)

# 4. Define the base class blueprint for relational tables
Base = declarative_base()

# 5. Dependency Injector function to manage individual endpoint lifecycles safely
async def get_db():
    """
    Yields a transactional database session context manager.
    Guarantees the path closes cleanly even if an extraction loop errors out.
    """
    session = async_session_local()
    try:
        yield session
    finally:
        await session.close()