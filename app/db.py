# app/db.py
import asyncio
from urllib.parse import urlparse
from typing import Optional

import motor.motor_asyncio
from pymongo.server_api import ServerApi
from beanie import init_beanie
from pymongo.errors import PyMongoError

from .config import settings
from .models.user import User
from .models.question import Question
from .models.test import TestSeries, TestSession, TestAttempt
from .models.user_analytics import UserAnalytics
from .models.admin_action import AdminAction
from .models.course import Course
from .models.study_material import StudyMaterial, UserMaterialProgress
from .models.exam_content import ExamContent
from .models.exam_category_structure import ExamCategoryStructure
from .models.contact import Contact

# Globals (one client + one beanie-init flag per process)
_global_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_client_lock = asyncio.Lock()

_beanie_initialized = False
_beanie_lock = asyncio.Lock()


async def _make_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Create a Motor client optimized for Vercel serverless environment.
    Key optimizations for serverless:
    - Minimal connection pool (serverless functions are single-use)
    - Fast timeouts to avoid hanging requests
    - Proper TLS and server API settings
    """
    return motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGO_URI,
        # Serverless-optimized settings
        serverSelectionTimeoutMS=3000,  # Faster timeout for serverless
        connectTimeoutMS=3000,          # Quick connection establishment
        socketTimeoutMS=10000,          # Reasonable socket timeout
        maxPoolSize=1,                  # Minimal pool for serverless (functions are ephemeral)
        minPoolSize=0,                  # No minimum connections
        maxIdleTimeMS=5000,             # Close idle connections quickly
        waitQueueTimeoutMS=3000,        # Don't wait too long for connections
        appname="pariksha-path-vercel",
        tls=True,
        tlsAllowInvalidCertificates=False,
        server_api=ServerApi("1"),
        # Additional serverless optimizations
        retryWrites=False,              # Disable retries for faster failures
        retryReads=False,               # Disable read retries
        compressors="zlib",             # Enable compression for better performance
    )


async def get_db_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get MongoDB client optimized for serverless environments.
    In serverless, we create a new connection per request for reliability.
    """
    global _global_client

    # For serverless environments, always create fresh connections
    # This avoids stale connection issues that cause BSON cursor errors
    try:
        if _global_client is not None:
            # Test if existing connection is healthy
            await _global_client.admin.command("ping", serverSelectionTimeoutMS=2000)
            return _global_client
        else:
            # Create new connection
            _global_client = await _make_client()
            await _global_client.admin.command("ping", serverSelectionTimeoutMS=2000)
            return _global_client

    except Exception as e:
        # Connection is unhealthy, create new one
        print(f"⚠️ Existing DB connection unhealthy: {str(e)}")
        try:
            if _global_client:
                _global_client.close()
        except Exception:
            pass

        _global_client = await _make_client()
        try:
            await _global_client.admin.command("ping", serverSelectionTimeoutMS=2000)
        except Exception as ping_error:
            print(f"❌ Failed to establish new DB connection: {str(ping_error)}")
            raise ping_error

        return _global_client


async def get_db_client_with_retry(max_retries: int = 2) -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get database client with retry logic for serverless environments.
    """
    for attempt in range(max_retries + 1):
        try:
            return await get_db_client()
        except Exception as e:
            if attempt == max_retries:
                print(f"❌ All DB connection attempts failed after {max_retries + 1} tries")
                raise e

            print(f"⚠️ DB connection attempt {attempt + 1} failed: {str(e)}")
            # Brief delay before retry
            await asyncio.sleep(0.1 * (attempt + 1))

    # This should never be reached, but just in case
    raise Exception("Failed to establish database connection after all retries")


async def init_db() -> None:
    """
    Initialize Beanie once per process. Safe to call repeatedly (idempotent).
    """
    global _beanie_initialized

    if _beanie_initialized:
        return

    async with _beanie_lock:
        if _beanie_initialized:
            return

        client = await get_db_client()

        # derive DB name from URI or fallback
        parsed = urlparse(settings.MONGO_URI)
        print(parsed)
        db_name = parsed.path.lstrip("/") or "pariksha_path_db"
        print(db_name)
        db = client.get_database(db_name)

        # register models with Beanie
        await init_beanie(
            database=db,
            document_models=[
                User,
                Question,
                TestAttempt,
                TestSeries,
                TestSession,
                UserAnalytics,
                AdminAction,
                Course,
                StudyMaterial,
                UserMaterialProgress,
                ExamCategoryStructure,
                ExamContent,
                Contact,
                # Material,
                # Result,
            ],
            allow_index_dropping=False,
        )

        _beanie_initialized = True


def close_client() -> None:
    """
    Close and drop the process-global client (useful during cleanup/tests).
    """
    global _global_client, _beanie_initialized
    try:
        if _global_client is not None:
            _global_client.close()
    except Exception:
        pass
    _global_client = None
    _beanie_initialized = False
