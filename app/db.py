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
from motor.motor_asyncio import AsyncIOMotorClient

# Global client (singleton)
client: AsyncIOMotorClient | None = None

async def init_db():
    try:
        global client
        if client is None:
            client = AsyncIOMotorClient(settings.MONGO_URI)
            
        # create motor client using MONGO_URI from settings
        # client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)

        # Test the connection
        await client.admin.command("ping")
        print("✅ Database connection successful! MongoDB is connected.")

        # Extract database name from MONGO_URI
        parsed_uri = urlparse(settings.MONGO_URI)
        db_name = parsed_uri.path.lstrip("/")  # Remove leading slash

        # If no database name in URI, use default
        if not db_name:
            db_name = "pariksha_path_db"
            print(f"⚠️  No database name found in MONGO_URI, using default: {db_name}")

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
        )
        print("✅ Beanie ODM initialized successfully!")

    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        raise e
