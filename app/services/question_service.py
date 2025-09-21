"""
Question service for question management operations
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import io

from ..models.question import (
    Question,
    QuestionType,
    DifficultyLevel,
    QuestionOption,
)
from ..models.test import TestSeries, TestDifficulty
from ..models.enums import ExamCategory
from .admin_service import AdminService


class QuestionService:
    """Service class for question management operations"""

    @staticmethod
    async def create_question_from_data(
        question_data: Dict[str, Any], created_by: str
    ) -> Question:
        """
        Create a Question object from structured data

        Args:
            question_data: Question data dictionary
            created_by: ID of the user creating the question

        Returns:
            Question object
        """
        # Process options
        options = []
        for i, option_data in enumerate(question_data.get("options", [])):
            options.append(
                QuestionOption(
                    text=option_data["text"],
                    is_correct=option_data["is_correct"],
                    order=i,
                    image_urls=option_data.get("image_urls", []),
                )
            )

        # Create question object
        question = Question(
            title=question_data["title"],
            question_text=question_data["question_text"],
            question_type=QuestionType(question_data["question_type"]),
            difficulty_level=DifficultyLevel(question_data["difficulty_level"]),
            exam_type=question_data["exam_type"],
            exam_year=question_data.get("exam_year"),
            options=options,
            explanation=question_data.get("explanation"),
            remarks=question_data.get("remarks"),
            subject=question_data["subject"],
            topic=question_data.get("topic", "General"),
            created_by=created_by,
            tags=question_data.get("tags", []),
            is_active=True,
            question_image_urls=question_data.get("question_image_urls", []),
            explanation_image_urls=question_data.get("explanation_image_urls", []),
            remarks_image_urls=question_data.get("remarks_image_urls", []),
        )

        return question

    @staticmethod
    async def process_csv_questions(
        df: pd.DataFrame,
        exam_category: ExamCategory,
        exam_subcategory: str,
        subject: str,
        topic: Optional[str],
        difficulty: DifficultyLevel,
        created_by: str,
    ) -> Tuple[List[Question], List[str]]:
        """
        Process CSV data into Question objects

        Args:
            df: Pandas DataFrame with question data
            exam_category: Exam category
            exam_subcategory: Exam subcategory
            subject: Subject
            topic: Topic (optional)
            difficulty: Difficulty level
            created_by: ID of the user creating questions

        Returns:
            Tuple of (questions_list, errors_list)
        """
        questions = []
        errors = []

        for idx, row in df.iterrows():
            try:
                # Process options
                options = []
                for i, opt in enumerate(["A", "B", "C", "D"]):
                    option_text = str(row[f"Option {opt}"]).strip()
                    is_correct = str(row["Correct Answer"]).strip().upper() == opt

                    options.append(
                        QuestionOption(
                            text=option_text,
                            is_correct=is_correct,
                            order=i,
                        )
                    )

                # Create question object
                question = Question(
                    title=str(row["Question"])[:50]
                    + ("..." if len(str(row["Question"])) > 50 else ""),
                    question_text=str(row["Question"]),
                    question_type=QuestionType.MCQ,
                    difficulty_level=difficulty,
                    exam_type=exam_subcategory,
                    options=options,
                    explanation=str(row.get("Explanation", "")).strip() or None,
                    remarks=str(row.get("Remarks", "")).strip() or None,
                    subject=subject,
                    topic=topic or "General",
                    created_by=created_by,
                    tags=[exam_category.value, exam_subcategory, subject],
                    is_active=True,
                )

                # Insert question into database
                await question.insert()
                questions.append(question)

            except Exception as e:
                errors.append(f"Error processing question at row {idx+1}: {str(e)}")

        return questions, errors

    @staticmethod
    async def update_question_data(
        question_id: str, update_data: Dict[str, Any]
    ) -> Tuple[Optional[Question], Dict[str, Any]]:
        """
        Update question data

        Args:
            question_id: Question ID
            update_data: Data to update

        Returns:
            Tuple of (updated_question, changes_made)
        """
        question = await Question.get(question_id)
        if not question:
            return None, {}

        changes = {}

        # Update fields if provided
        for field, value in update_data.items():
            if value is not None:
                # Special handling for options
                if field == "options" and isinstance(value, list):
                    question_options = []
                    for i, option_data in enumerate(value):
                        if (
                            not isinstance(option_data, dict)
                            or "text" not in option_data
                            or "is_correct" not in option_data
                        ):
                            raise ValueError(
                                "Invalid options format. Each option must have 'text' and 'is_correct' fields"
                            )

                        question_options.append(
                            QuestionOption(
                                text=option_data["text"],
                                is_correct=option_data["is_correct"],
                                order=option_data.get("order", i),
                            )
                        )
                    value = question_options

                # Handle field mapping for enum fields
                if field == "question_type" and isinstance(value, str):
                    value = QuestionType(value)

                if field == "difficulty_level" and isinstance(value, str):
                    value = DifficultyLevel(value)

                # Set the new value
                setattr(question, field, value)
                changes[field] = (
                    str(value) if not isinstance(value, list) else "updated"
                )

        # Only update if there are changes
        if changes:
            question.update_timestamp()
            await question.save()

        return question, changes

    @staticmethod
    async def get_question_by_id(question_id: str) -> Optional[Question]:
        """
        Get question by ID

        Args:
            question_id: Question ID

        Returns:
            Question object if found, None otherwise
        """
        return await Question.get(question_id)

    @staticmethod
    async def delete_question(question_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a question

        Args:
            question_id: Question ID

        Returns:
            Question details if deleted, None if not found
        """
        question = await Question.get(question_id)
        if not question:
            return None

        # Store question details for audit log
        question_details = {
            "title": question.title,
            "question_text": question.question_text,
            "subject": question.subject,
            "topic": question.topic,
        }

        # Delete the question
        await question.delete()

        return question_details

    @staticmethod
    async def get_questions_for_test(test_id: str) -> List[Question]:
        """
        Get all questions for a specific test

        Args:
            test_id: Test ID

        Returns:
            List of Question objects
        """
        test = await TestSeries.get(test_id)
        if not test or not test.question_ids:
            return []

        questions = await Question.find({"_id": {"$in": test.question_ids}}).to_list()

        return questions

    @staticmethod
    async def create_or_update_test_with_questions(
        questions: List[Question],
        test_title: str,
        exam_category: ExamCategory,
        exam_subcategory: str,
        subject: str,
        duration_minutes: int,
        is_free: bool,
        created_by: str,
        existing_test_id: Optional[str] = None,
    ) -> TestSeries:
        """
        Create or update a test series with questions

        Args:
            questions: List of Question objects
            test_title: Test title
            exam_category: Exam category
            exam_subcategory: Exam subcategory
            subject: Subject
            duration_minutes: Test duration in minutes
            is_free: Whether test is free
            created_by: ID of the user creating the test
            existing_test_id: Existing test ID to update (optional)

        Returns:
            TestSeries object
        """
        if existing_test_id:
            # Update existing test
            test_series = await TestSeries.get(existing_test_id)
            if not test_series:
                raise ValueError(f"Test with ID {existing_test_id} not found")

            # Add new questions to existing test
            question_ids = [str(q.id) for q in questions]
            test_series.question_ids.extend(question_ids)
            test_series.total_questions = len(test_series.question_ids)
            await test_series.save()
        else:
            # Create new test series
            test_series = TestSeries(
                title=test_title,
                description=f"{test_title} for {exam_subcategory}",
                exam_category=exam_category.value,
                exam_subcategory=exam_subcategory,
                subject=subject,
                total_questions=len(questions),
                duration_minutes=duration_minutes,
                max_score=len(questions),  # 1 point per question
                difficulty=TestDifficulty.MEDIUM,  # Default difficulty
                question_ids=[str(q.id) for q in questions],
                is_free=is_free,
                created_by=created_by,
            )
            await test_series.insert()

        return test_series
