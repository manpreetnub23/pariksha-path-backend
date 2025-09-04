import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from faker import Faker
from bson import ObjectId
import random
import string

import os
import sys

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Import models
from app.models.user import User
from app.models.question import Question
from app.models.test_attempt import TestAttempt
from app.models.test_series import TestSeries, TestDifficulty
from app.models.user_analytics import UserAnalytics
from app.models.admin_action import AdminAction
from app.models.course import Course
from app.models.material import Material
from app.models.study_material import StudyMaterial, UserMaterialProgress
from app.models.result import Result
from app.models.exam_category_structure import ExamCategoryStructure
from app.models.enums import (
    ExamCategory,
    UserRole,
    MaterialType,
    MaterialAccessType,
    MaterialCategory
)

from app.db import init_db

fake = Faker()

# Common data
exam_categories = [e.value for e in ExamCategory][:5]
subjects = ["Mathematics", "Physics", "Chemistry", "Biology", "English", "Reasoning"]
difficulty_levels = [e.value for e in TestDifficulty]
material_types = [e.value for e in MaterialType]
access_types = [e.value for e in MaterialAccessType]
material_categories = [e.value for e in MaterialCategory]


def get_random_id() -> str:
    return str(ObjectId())


def get_random_timestamp(days_ago: int = 365):
    return datetime.now(timezone.utc) - timedelta(days=random.randint(1, days_ago))


async def create_admin_user() -> User:
    """Create an admin user with predefined credentials."""
    admin = User(
        name="Admin User",
        email="admin@example.com",
        phone="9876543210",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 'password'
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
        has_premium_access=True,
        preferred_exam_categories=[],
        settings={
            "theme": "dark",
            "notifications": True,
            "email_updates": True
        },
        ui_preferences={
            "theme": "dark",
            "font_size": "medium",
            "density": "normal"
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await admin.create()
    return admin


async def create_users(count: int = 10) -> List[User]:
    users = []
    for _ in range(count):
        is_active = random.choice([True, True, True, False])  # 75% active
        is_verified = random.choice([True, False])
        has_premium = random.choice([True, False, False, False])  # 25% premium
        
        user = User(
            name=fake.name(),
            email=fake.email(),
            phone=fake.phone_number()[:15],
            password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # 'password'
            role=random.choice([UserRole.STUDENT, UserRole.ADMIN]),
            is_active=is_active,
            is_verified=is_verified,
            is_email_verified=is_verified,
            preferred_exam_categories=random.sample(exam_categories, k=random.randint(1, 3)),
            has_premium_access=has_premium,
            dashboard_settings={
                "theme": random.choice(["light", "dark"]),
                "notifications": True,
                "email_updates": random.choice([True, False])
            },
            ui_preferences={
                "theme": random.choice(["light", "dark"]),
                "font_size": random.choice(["small", "medium", "large"]),
                "density": random.choice(["compact", "normal", "comfortable"])
            },
            created_at=get_random_timestamp(365),
            updated_at=get_random_timestamp(30),
        )
        await user.create()
        users.append(user)
    return users


async def create_courses(count: int = 5, creator: User = None) -> List[Course]:
    courses = []
    for _ in range(count):
        is_free = random.choice([True, True, False])  # 2/3 chance of being free
        price = 0 if is_free else random.choice([999, 1999, 2999, 4999])
        
        course = Course(
            title=f"{fake.word().title()} {fake.word().title()} Course",
            description=fake.paragraph(),
            code=f"{random.choice(['BIO', 'PHY', 'CHEM', 'MATH', 'ENG'])}{random.randint(100, 999)}",
            category=random.choice(exam_categories),
            sub_category=random.choice(["Crash Course", "Full Course", "Revision"]),
            price=price,
            is_free=is_free,
            duration_weeks=random.randint(4, 24),  # Random duration between 4 to 24 weeks
            created_by=str(creator.id) if creator else "system",  # Default to "system" if no creator provided
            discount_percent=random.choice([0, 0, 0, 10, 20, 30]),  # Mostly no discount
            thumbnail_url=f"https://picsum.photos/400/200?random={random.randint(1,1000)}",
            icon_url=f"https://picsum.photos/100/100?random={random.randint(1,1000)}",
            banner_url=f"https://picsum.photos/1200/300?random={random.randint(1,1000)}",
            tagline=fake.sentence(),
            instructor_id=str(creator.id) if creator else None,
            created_at=get_random_timestamp(180),
            updated_at=get_random_timestamp(30)
        )
        await course.create()
        courses.append(course)
    return courses


async def create_test_series(
    count: int = 10, course: Course = None, creator: User = None
) -> List[TestSeries]:
    test_series = []
    for _ in range(count):
        difficulty = random.choice(difficulty_levels)
        duration = random.choice([30, 45, 60, 90, 120])
        total_questions = random.randint(30, 100)
        
        series = TestSeries(
            title=f"{fake.word().title()} Test Series",
            description=fake.paragraph(),
            exam_category=course.category if course else random.choice(exam_categories),
            exam_subcategory=random.choice(["NEET", "JEE Main", "GATE", "UPSC"]),
            subject=random.choice(subjects),
            total_questions=total_questions,
            duration_minutes=duration,
            max_score=total_questions * 4,  # Assuming 4 marks per question
            difficulty=TestDifficulty(difficulty),
            is_free=random.choice([True, False, False]),
            price=random.choice([0, 0, 0, 499, 999, 1499]),
            instructions=f"This test contains {total_questions} questions to be completed in {duration} minutes.",
            created_by=str(creator.id) if creator else "system",
            created_at=get_random_timestamp(90),
            updated_at=get_random_timestamp(15)
        )
        await series.create()
        test_series.append(series)
    return test_series


async def create_questions(test_series: TestSeries, count: int = 10, creator: User = None) -> List[Question]:
    questions = []
    for i in range(count):
        options = [
            {"text": fake.sentence(), "is_correct": False} for _ in range(3)
        ]
        # Add one correct answer
        correct_option = {"text": fake.sentence(), "is_correct": True}
        options.insert(random.randint(0, 3), correct_option)
        
        question = Question(
            title=f"Question {i+1} - {fake.word().title()}",
            question_text=f"{fake.sentence()}?",
            question_type=random.choice(["mcq", "true_false"]),
            difficulty_level=random.choice(["easy", "medium", "hard"]),
            exam_type=test_series.exam_subcategory or "General",
            options=options,
            explanation=fake.paragraph() if random.choice([True, False]) else "",
            subject=test_series.subject or random.choice(subjects),
            topic=random.choice(["Mechanics", "Algebra", "Organic Chemistry", "Electromagnetism"]),
            created_by=str(creator.id) if creator else "system",
            test_series_id=str(test_series.id),
            created_at=get_random_timestamp(60),
            updated_at=get_random_timestamp(15)
        )
        await question.create()
        questions.append(question)
    return questions


async def create_test_attempts(
    user: User, test_series: TestSeries, count: int = 3
) -> List[TestAttempt]:
    attempts = []
    for _ in range(count):
        is_completed = random.choice([True, True, False])  # 2/3 chance of completion
        start_time = get_random_timestamp(30)
        end_time = start_time + timedelta(minutes=test_series.duration_minutes) if is_completed else None
        total_questions = test_series.total_questions
        
        attempt = TestAttempt(
            user_id=str(user.id),
            test_series_id=str(test_series.id),
            start_time=start_time,
            end_time=end_time,
            is_completed=is_completed,
            score=random.randint(30, 95) if is_completed else 0,
            max_score=test_series.max_score,
            total_questions=total_questions,
            time_spent_seconds=test_series.duration_minutes * 60 if is_completed else random.randint(0, test_series.duration_minutes * 60),
            created_at=start_time,
            updated_at=end_time or start_time,
        )
        await attempt.create()
        attempts.append(attempt)
    return attempts


async def create_study_materials(
    count: int = 10, course: Course = None, creator: User = None
) -> List[StudyMaterial]:
    materials = []
    for _ in range(count):
        mat_type = random.choice(material_types)
        mat_category = random.choice(material_categories)
        access_type = random.choice(access_types)
        exam_category = course.category if course else random.choice(exam_categories)
        subject = random.choice(subjects)
        
        material = StudyMaterial(
            title=f"{fake.word().title()} {mat_category.replace('_', ' ').title()}",
            description=fake.paragraph(),
            format=mat_type,
            category=mat_category,
            file_url=f"https://example.com/materials/{fake.uuid4()}.pdf",
            file_size_kb=random.randint(1024, 10240),  # 1MB to 10MB
            preview_url=f"https://picsum.photos/800/1200?random={random.randint(1,1000)}",
            thumbnail_url=f"https://picsum.photos/300/200?random={random.randint(1,1000)}",
            access_type=access_type,
            exam_category=exam_category,
            exam_subcategory=random.choice(["NEET", "JEE", "UPSC", "SSC"]),
            subject=subject,
            topic=random.choice(["Mechanics", "Algebra", "Organic Chemistry", "Electromagnetism"]),
            tags=[fake.word() for _ in range(random.randint(1, 5))],
            course_ids=[str(course.id)] if course else [],
            created_by=str(creator.id) if creator else "system",
            created_at=get_random_timestamp(60),
            updated_at=get_random_timestamp(15),
        )
        await material.create()
        materials.append(material)
    return materials


async def create_user_analytics(users: List[User]) -> List[UserAnalytics]:
    analytics = []
    for user in users:
        total_tests = random.randint(0, 50)
        avg_score = random.uniform(30, 95)
        
        # Generate subject-wise analytics
        subject_analytics = {}
        for subject in random.sample(subjects, k=random.randint(1, len(subjects))):
            subject_analytics[subject] = {
                "tests_taken": random.randint(0, total_tests),
                "average_score": random.uniform(30, 100),
                "strength": random.choice(["strong", "average", "weak"]),
                "last_attempted": get_random_timestamp(30).isoformat(),
                "improvement": random.uniform(-10, 10)  # Percentage improvement
            }
        
        # Generate test history
        test_history = []
        for _ in range(random.randint(0, 10)):  # Last 10 tests
            test_history.append({
                "test_id": get_random_id(),
                "test_name": f"{random.choice(['Weekly', 'Monthly', 'Mock'])} Test {random.randint(1, 100)}",
                "score": random.randint(30, 100),
                "max_score": 100,
                "date": get_random_timestamp(30).isoformat(),
                "subject": random.choice(subjects),
                "time_spent": random.randint(300, 7200)  # 5 mins to 2 hours
            })
        
        analytic = UserAnalytics(
            user_id=str(user.id),
            user_email=user.email,
            user_name=user.name,
            total_tests_taken=total_tests,
            total_time_spent=random.randint(0, 100) * 60,  # in seconds
            average_score=avg_score,
            rank=random.randint(1, 1000) if total_tests > 0 else None,
            percentile=random.uniform(0, 100) if total_tests > 0 else None,
            test_history=test_history,
            subject_analytics=subject_analytics,
            created_at=get_random_timestamp(30),
            updated_at=get_random_timestamp(1),
        )
        await analytic.create()
        analytics.append(analytic)
    return analytics


async def create_admin_actions(admin: User, count: int = 5) -> List[AdminAction]:
    actions = []
    action_types = ["create", "update", "delete"]  # Must match ActionType enum
    target_collections = ["users", "courses", "test_series", "questions", "study_materials"]
    
    for _ in range(count):
        target_collection = random.choice(target_collections)
        field = random.choice(["status", "price", "content", "title", "description"])
        old_value = f"old_{field}"
        new_value = f"new_{field}"
        
        action = AdminAction(
            admin_id=str(admin.id),
            action_type=action_types[random.randint(0, 2)],  # Random action type
            target_collection=target_collection,
            target_id=get_random_id(),
            changes={
                field: {"from": old_value, "to": new_value},
                "updated_at": get_random_timestamp(30).isoformat()
            },
            timestamp=get_random_timestamp(30)
        )
        await action.create()
        actions.append(action)
    return actions


async def create_exam_category_structure(admin_id: str) -> ExamCategoryStructure:
    structure = {
        "Engineering": ["JEE Main", "JEE Advanced", "BITSAT", "VITEEE"],
        "Medical": ["NEET", "AIIMS", "JIPMER"],
        "Defence": ["NDA", "CDS", "AFCAT"],
        "Civil Services": ["UPSC CSE", "State PSC"],
        "Banking": ["IBPS PO", "SBI PO", "RBI Grade B"],
    }

    exam_structure = ExamCategoryStructure(
        structure=structure,
        version=1,
        is_active=True,
        created_by=admin_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await exam_structure.create()
    return exam_structure


async def main():
    print("🚀 Starting data seeding...")

    # Initialize database connection using project's db module
    from app.db import init_db
    await init_db()

    # Clear existing data (be careful in production!)
    if input("⚠️  Clear existing data? (y/n): ").lower() == "y":
        # Delete all documents from each collection
        for model in [
            User,
            Question,
            TestAttempt,
            TestSeries,
            UserAnalytics,
            AdminAction,
            Course,
            Material,
            StudyMaterial,
            UserMaterialProgress,
            Result,
            ExamCategoryStructure,
        ]:
            await model.delete_all()
            print(f"🗑️  Cleared {model.__name__} collection")
        print("✅ All collections cleared")

    # Create admin user
    print("👨‍💼 Creating admin user...")
    admin = await create_admin_user()
    
    # Create exam category structure with admin ID
    print("📝 Creating exam category structure...")
    await create_exam_category_structure(str(admin.id))

    # Create regular users
    print(f"👥 Creating users...")
    users = await create_users(20)
    users.append(admin)  # Add admin to users list

    # Create courses
    print(f"📚 Creating courses...")
    courses = []
    for _ in range(10):
        course_creator = random.choice(users)
        new_courses = await create_courses(1, course_creator)
        if new_courses:  # Check if any courses were returned
            courses.append(new_courses[0])

    # Create test series and questions
    print(f"📝 Creating test series and questions...")
    test_series_list = []
    for course in courses:
        series = await create_test_series(3, course, random.choice(users))  # 3 test series per course
        test_series_list.extend(series)

        for test in series:
            await create_questions(test, 15, random.choice(users))  # 15 questions per test

    # Create test attempts
    print(f"📊 Creating test attempts...")
    for user in users:
        for _ in range(random.randint(1, 5)):  # 1-5 test attempts per user
            test_series = random.choice(test_series_list)
            await create_test_attempts(user, test_series, random.randint(1, 3))

    # Create study materials
    print(f"📖 Creating study materials...")
    for course in courses:
        await create_study_materials(5, course, random.choice(users))  # 5 materials per course

    # Create user analytics
    print(f"📈 Creating user analytics...")
    await create_user_analytics(users)

    # Create admin actions
    print(f"👨‍💼 Creating admin actions...")
    await create_admin_actions(admin, 10)

    print("✅ Data seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
