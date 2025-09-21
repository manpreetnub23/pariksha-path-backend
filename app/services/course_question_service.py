"""
Course question service for question management within course sections
"""

from typing import Dict, Any, List, Optional
import csv
import io
from bson import ObjectId

from ..models.course import Course
from ..models.question import Question, QuestionType, DifficultyLevel, QuestionOption
from ..models.admin_action import AdminAction, ActionType
from ..models.user import User
from ..config import settings
from .admin_service import AdminService


class CourseQuestionService:
    """Service class for course question management operations"""

    @staticmethod
    async def upload_questions_to_section(
        course_id: str, section: str, file_content: bytes, current_user: User
    ) -> Dict[str, Any]:
        """
        Upload questions to a specific section in a course

        Args:
            course_id: Course ID
            section: Section name
            file_content: CSV file content
            current_user: User uploading questions

        Returns:
            Dictionary with upload result
        """
        # Validate course_id
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        # Get the course
        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Validate section exists in course
        section_names = course.get_section_names()
        if not section_names or section not in section_names:
            raise ValueError(f"Section '{section}' not found in course")

        # Read and parse CSV file
        text = file_content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(text))

        questions = []
        for row in csv_reader:
            try:
                # Extract options with correct format
                options = []
                correct_answer = row.get("correct_answer", "").strip().upper()
                remarks = row.get("remarks", "").strip()
                for i, opt_key in enumerate(
                    ["option_a", "option_b", "option_c", "option_d"]
                ):
                    opt_text = row.get(opt_key, "").strip()
                    if opt_text:
                        option_letter = chr(65 + i)  # A, B, C, D
                        options.append(
                            QuestionOption(
                                text=opt_text,
                                is_correct=option_letter == correct_answer,
                                order=i,
                            )
                        )

                # Get question text and create title
                question_text = row.get("question", "").strip()
                title = question_text[:50] + ("..." if len(question_text) > 50 else "")

                # Extract explanation and remarks
                explanation = row.get("explanation", "").strip() or None

                # Map CSV row to Question model
                question = Question(
                    title=title,
                    question_text=question_text,
                    question_type=QuestionType.MCQ,
                    difficulty_level=DifficultyLevel.MEDIUM,  # Default difficulty
                    course_id=course_id,
                    section=section,
                    options=options,
                    explanation=explanation,
                    remarks=remarks or None,
                    subject=row.get("subject", "General").strip(),
                    topic=row.get("topic", "General").strip(),
                    tags=[],
                    created_by=str(current_user.id),
                )
                questions.append(question)
            except Exception as e:
                print(f"Error processing row: {row}. Error: {str(e)}")
                continue

        # Save questions to database
        if questions:
            await Question.insert_many(questions)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.CREATE,
            "questions",
            course_id,
            {
                "action": "questions_uploaded",
                "count": len(questions),
                "section": section,
            },
        )

        return {
            "status": "success",
            "message": f"Successfully uploaded {len(questions)} questions to section '{section}'",
            "count": len(questions),
        }

    @staticmethod
    async def get_section_questions(
        course_id: str,
        section_name: str,
        page: int = 1,
        limit: int = 10,
        difficulty: Optional[str] = None,
        topic: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get questions for a specific section in a course

        Args:
            course_id: Course ID
            section_name: Name of the section
            page: Page number
            limit: Items per page
            difficulty: Filter by difficulty
            topic: Filter by topic
            mode: Mode (normal | mock)

        Returns:
            Dictionary with questions and pagination info
        """
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        section = course.get_section(section_name)
        if not section:
            raise ValueError(f"Section '{section_name}' not found in course")

        # MOCK MODE
        if (mode or "").lower() == "mock":
            question_limit = int(section.question_count or 0)
            if question_limit <= 0:
                return {
                    "message": f"No questions configured for section '{section_name}'",
                    "course": {
                        "id": str(course.id),
                        "title": course.title,
                        "code": course.code,
                    },
                    "section": section_name,
                    "questions": [],
                    "pagination": {
                        "total": 0,
                        "limit": question_limit,
                        "page": 1,
                        "total_pages": 0,
                    },
                }

            from motor.motor_asyncio import AsyncIOMotorClient

            _client = AsyncIOMotorClient(settings.MONGO_URI)
            db = _client.get_default_database()
            collection = db["questions"]

            pipeline = [
                {"$match": {"course_id": course_id, "section": section_name}},
                {"$sample": {"size": question_limit}},
            ]

            cursor = collection.aggregate(pipeline)

            questions = []
            async for doc in cursor:
                if "_id" in doc:
                    doc["id"] = str(doc["_id"])
                questions.append(doc)

            total_questions = len(questions)
            total_pages = 1

        # NORMAL MODE
        else:
            query_filters = {"course_id": course_id, "section": section_name}
            if difficulty:
                query_filters["difficulty_level"] = difficulty.upper()
            if topic:
                query_filters["topic"] = {"$regex": topic, "$options": "i"}

            skip = (page - 1) * limit
            questions = (
                await Question.find(query_filters)
                .sort([("created_at", -1)])
                .skip(skip)
                .limit(limit)
                .to_list()
            )

            total_questions = await Question.find(query_filters).count()
            total_pages = (total_questions + limit - 1) // limit

        # FORMAT RESPONSE (handle dicts + Beanie models)
        question_data = []
        for q in questions:
            if isinstance(q, dict):  # MOCK MODE
                options_with_images = [
                    {
                        "text": opt.get("text"),
                        "is_correct": opt.get("is_correct", False),
                        "order": opt.get("order"),
                        "image_urls": opt.get("image_urls", []),
                    }
                    for opt in q.get("options", [])
                ]

                question_data.append(
                    {
                        "id": str(q.get("id", q.get("_id"))),
                        "title": q.get("title"),
                        "question_text": q.get("question_text"),
                        "question_type": q.get("question_type"),
                        "difficulty_level": q.get("difficulty_level"),
                        "options": options_with_images,
                        "explanation": q.get("explanation"),
                        "remarks": q.get("remarks"),
                        "subject": q.get("subject"),
                        "topic": q.get("topic"),
                        "tags": q.get("tags", []),
                        "marks": q.get("marks", 1.0),
                        "created_at": q.get("created_at"),
                        "updated_at": q.get("updated_at"),
                        "is_active": q.get("is_active", True),
                        "created_by": q.get("created_by"),
                        "question_image_urls": q.get("question_image_urls", []),
                        "explanation_image_urls": q.get("explanation_image_urls", []),
                        "remarks_image_urls": q.get("remarks_image_urls", []),
                    }
                )
            else:  # NORMAL MODE
                options_with_images = [
                    {
                        "text": option.text,
                        "is_correct": option.is_correct,
                        "order": option.order,
                        "image_urls": option.image_urls,
                    }
                    for option in q.options
                ]

                question_data.append(
                    {
                        "id": str(q.id),
                        "title": q.title,
                        "question_text": q.question_text,
                        "question_type": getattr(
                            q.question_type, "value", str(q.question_type)
                        ),
                        "difficulty_level": getattr(
                            q.difficulty_level, "value", str(q.difficulty_level)
                        ),
                        "options": options_with_images,
                        "explanation": q.explanation,
                        "remarks": q.remarks,
                        "subject": q.subject,
                        "topic": q.topic,
                        "tags": q.tags,
                        "marks": getattr(q, "marks", 1.0),
                        "created_at": q.created_at,
                        "updated_at": q.updated_at,
                        "is_active": q.is_active,
                        "created_by": q.created_by,
                        "question_image_urls": q.question_image_urls,
                        "explanation_image_urls": q.explanation_image_urls,
                        "remarks_image_urls": q.remarks_image_urls,
                    }
                )

        return {
            "message": (
                f"Random {section.question_count} questions for section '{section_name}' (mock mode)"
                if (mode or "").lower() == "mock"
                else f"Questions for section '{section_name}' retrieved successfully"
            ),
            "course": {
                "id": str(course.id),
                "title": course.title,
                "code": course.code,
            },
            "section": section_name,
            "questions": question_data,
            "pagination": (
                {
                    "total": total_questions,
                    "limit": section.question_count,
                    "page": 1,
                    "total_pages": total_pages,
                }
                if (mode or "").lower() == "mock"
                else {
                    "total": total_questions,
                    "page": page,
                    "limit": limit,
                    "total_pages": total_pages,
                }
            ),
        }
