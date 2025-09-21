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

# from .models.material import Material
from .models.study_material import StudyMaterial, UserMaterialProgress
from .models.exam_category_structure import ExamCategoryStructure

# from .models.result import Result  # enable if needed

# Globals (one client + one beanie-init flag per process)
_global_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_client_lock = asyncio.Lock()

_beanie_initialized = False
_beanie_lock = asyncio.Lock()


async def _make_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Create a Motor client tuned for serverless. Adjust pool sizes/timeouts for your load.
    """
    return motor.motor_asyncio.AsyncIOMotorClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=20000,
        maxPoolSize=2,  # small pool for serverless
        minPoolSize=0,
        maxIdleTimeMS=10000,  # close idle faster
        waitQueueTimeoutMS=5000,
        appname="pariksha-path-vercel",
        tls=True,
        tlsAllowInvalidCertificates=False,
        server_api=ServerApi("1"),
    )


async def get_db_client() -> motor.motor_asyncio.AsyncIOMotorClient:
    """
    Return a long-lived client for this process. Recreate if ping fails.
    Safe for concurrent cold-starts via an async lock.
    """
    global _global_client

    # fast path: existing client and healthy
    if _global_client is not None:
        try:
            await _global_client.admin.command("ping")
            return _global_client
        except Exception:
            try:
                _global_client.close()
            except Exception:
                pass
            _global_client = None

    # guarded creation to avoid concurrent double-init
    async with _client_lock:
        if _global_client is not None:
            # another coroutine already created it
            try:
                await _global_client.admin.command("ping")
                return _global_client
            except Exception:
                try:
                    _global_client.close()
                except Exception:
                    pass
                _global_client = None

        # create client
        _global_client = await _make_client()
        try:
            await _global_client.admin.command("ping")
        except Exception:
            # ping failed; leave client assigned so callers can decide;
            # get_db_client callers should handle errors if ping is required.
            pass

    return _global_client


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
        db_name = parsed.path.lstrip("/") or "pariksha_path_db"
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
