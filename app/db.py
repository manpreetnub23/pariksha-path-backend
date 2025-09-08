import motor.motor_asyncio
from beanie import init_beanie
from .models.user import User
from .models.question import Question
from .models.test import TestSeries, TestSession, TestAttempt
from .models.user_analytics import UserAnalytics
from .models.admin_action import AdminAction
from .models.course import Course
from .models.material import Material
from .models.study_material import StudyMaterial, UserMaterialProgress

# from .models.blog import Blog
from .models.result import Result

# from .models.payment import Payment
# from .models.notification import Notification
# from .models.contact import Contact
from .models.exam_category_structure import ExamCategoryStructure
from .config import settings
from urllib.parse import urlparse


# Keep a global client reference
_global_client = None


async def get_db_client():
    """Get or create a MongoDB client"""
    global _global_client

    if _global_client is None:
        # Create new client with connection pooling optimized for serverless
        print("🔄 Creating new MongoDB client...")
        _global_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            maxPoolSize=10,  # Limit connection pool for serverless
            minPoolSize=0,  # Don't keep idle connections open
            maxIdleTimeMS=30000,  # Close idle connections after 30 seconds
            connectTimeoutMS=5000,  # Connection timeout
            retryWrites=True,  # Retry failed write operations
            socketTimeoutMS=20000,  # Socket timeout
        )

    return _global_client


async def init_db():
    """Initialize database and register models"""
    try:
        # Log the start of initialization
        print("🔄 Initializing MongoDB connection...")

        # Get client (creates new one if needed)
        client = await get_db_client()

        # Test the connection with short timeout
        try:
            await client.admin.command("ping", socketTimeoutMS=5000)
            print("✅ Database connection successful! MongoDB is connected.")
        except Exception as e:
            print(f"⚠️ Ping failed, but continuing: {str(e)}")

        # Extract database name from MONGO_URI
        parsed_uri = urlparse(settings.MONGO_URI)
        db_name = parsed_uri.path.lstrip("/")  # Remove leading slash

        # If no database name in URI, use default
        if not db_name:
            db_name = "pariksha_path_db"
            print(f"⚠️ No database name found in MONGO_URI, using default: {db_name}")

        print(f"📁 Using database: {db_name}")
        db = client.get_database(db_name)

        # Register all document models
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
                Material,
                StudyMaterial,
                UserMaterialProgress,
                # Blog,
                # Result,
                # Payment,
                # Notification,
                # Contact,
                ExamCategoryStructure,
            ],
            allow_index_dropping=False,  # Safer for production
        )
        print("✅ Beanie ODM initialized successfully!")
        return client  # Return client for potential cleanup later

    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        # Print detailed connection error to help with debugging
        if "MONGO_URI" in str(e).upper():
            print("⚠️ Check that your MONGO_URI environment variable is correctly set")
        raise e
