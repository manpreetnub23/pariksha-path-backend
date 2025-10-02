# app/db.py
import asyncio
from urllib.parse import urlparse
from typing import Optional
import os
import time

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
_db_name = None  # Cache the database name
_init_in_progress = False  # Prevent race conditions
_last_init_time = 0  # Track when we last initialized

# Environment variable to track if we're in a serverless environment
_is_serverless = (
    os.environ.get("VERCEL") == "1"
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
)


async def _make_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Create a Motor client optimized for Vercel serverless environment.
    """
    return motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGO_URI,
        # Serverless-optimized settings
        serverSelectionTimeoutMS=3000,
        connectTimeoutMS=3000,
        socketTimeoutMS=10000,
        maxPoolSize=5 if _is_serverless else 10,  # Slightly larger pool for serverless
        minPoolSize=1 if _is_serverless else 0,  # Keep at least one connection alive
        maxIdleTimeMS=30000,  # Keep connections alive longer
        waitQueueTimeoutMS=3000,
        appname="pariksha-path-vercel",
        tls=True,
        tlsAllowInvalidCertificates=False,
        server_api=ServerApi("1"),
        # Additional serverless optimizations
        retryWrites=True,  # Enable retries for reliability
        retryReads=True,  # Enable read retries
        compressors="zlib",
    )


async def get_db_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get MongoDB client optimized for serverless environments.
    """
    global _global_client, _db_name

    # Cache the database name
    if _db_name is None:
        parsed = urlparse(settings.MONGO_URI)
        _db_name = parsed.path.lstrip("/") or "pariksha_path_db"

    # Try to use existing connection if it's healthy
    if _global_client is not None:
        try:
            # Quick ping to check if connection is alive
            await _global_client.admin.command("ping", serverSelectionTimeoutMS=1000)
            return _global_client
        except Exception as e:
            print(f"⚠ Existing DB connection unhealthy: {str(e)}")
            # Don't close here, just create a new one

    # Create new connection
    try:
        _global_client = await _make_client()
        await _global_client.admin.command("ping", serverSelectionTimeoutMS=2000)
        print("✅ New DB connection established")
        return _global_client
    except Exception as e:
        print(f"❌ Failed to establish DB connection: {str(e)}")
        raise


async def init_beanie_if_needed() -> None:
    """
    Initialize Beanie only if needed, with proper locking.
    This is the key function that prevents repeated initializations.
    """
    global _beanie_initialized, _init_in_progress, _last_init_time

    # Fast path - already initialized
    if _beanie_initialized:
        return

    # Prevent multiple initializations
    if _init_in_progress:
        # Wait for initialization to complete
        while _init_in_progress:
            await asyncio.sleep(0.1)
        return

    async with _beanie_lock:
        # Double-check after acquiring lock
        if _beanie_initialized:
            return

        _init_in_progress = True
        try:
            start_time = time.time()
            client = await get_db_client()

            # Use cached database name
            if _db_name is None:
                parsed = urlparse(settings.MONGO_URI)
                _db_name = parsed.path.lstrip("/") or "pariksha_path_db"

            db = client.get_database(_db_name)

            # Register models with Beanie
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
                ],
                allow_index_dropping=False,
            )

            _beanie_initialized = True
            _last_init_time = time.time()
            elapsed = time.time() - start_time
            print(f"✅ Beanie models initialized successfully in {elapsed:.2f}s")
        except Exception as e:
            print(f"❌ Beanie initialization failed: {str(e)}")
            raise
        finally:
            _init_in_progress = False


async def init_db() -> None:
    """
    Legacy function for backward compatibility.
    """
    await init_beanie_if_needed()


async def get_db_client_with_retry(
    max_retries: int = 2,
) -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Get database client with retry logic for serverless environments.
    """
    for attempt in range(max_retries + 1):
        try:
            return await get_db_client()
        except Exception as e:
            if attempt == max_retries:
                print(
                    f"❌ All DB connection attempts failed after {max_retries + 1} tries"
                )
                raise e

            print(f"⚠ DB connection attempt {attempt + 1} failed: {str(e)}")
            # Brief delay before retry
            await asyncio.sleep(0.1 * (attempt + 1))

    # This should never be reached, but just in case
    raise Exception("Failed to establish database connection after all retries")


def close_client() -> None:
    """
    Close and drop the process-global client (useful during cleanup/tests).
    """
    global _global_client, _beanie_initialized, _db_name
    try:
        if _global_client is not None:
            _global_client.close()
    except Exception:
        pass
    _global_client = None
    _beanie_initialized = False
    _db_name = None