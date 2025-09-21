"""
Mock test service for course-based mock testing functionality
"""

from typing import Dict, Any, List, Optional
from bson import ObjectId

from ..models.course import Course
from ..models.question import Question
from ..models.user import User


class MockTestService:
    """Service class for mock test operations"""

    @staticmethod
    def str_to_bool(value: str) -> Optional[bool]:
        """
        Convert string to boolean

        Args:
            value: String value to convert

        Returns:
            Boolean value or None if invalid
        """
        if value is None:
            return None
        if value.lower() in ["true", "1", "yes"]:
            return True
        if value.lower() in ["false", "0", "no"]:
            return False
        return None

    @staticmethod
    async def list_tests(is_free: Optional[str] = None) -> Dict[str, Any]:
        """
        List available tests

        Args:
            is_free: Filter by free status

        Returns:
            Dictionary with tests list
        """
        from ..models.test import TestSeries

        query = {}
        parsed_bool = MockTestService.str_to_bool(is_free)
        if parsed_bool is not None:
            query["is_free"] = parsed_bool

        tests = await TestSeries.find(query).to_list()
        return {"items": tests, "message": "Tests retrieved successfully"}

    @staticmethod
    async def submit_course_mock(
        course_id: str,
        answers: List[Dict[str, Any]],
        time_spent_seconds: int,
        current_user: User,
    ) -> Dict[str, Any]:
        """
        Score submitted answers for a course-based mock

        Args:
            course_id: Course ID
            answers: List of answers
            time_spent_seconds: Time spent on the test
            current_user: User submitting the mock

        Returns:
            Dictionary with mock test results
        """
        # Validate course
        if not ObjectId.is_valid(course_id):
            raise ValueError("Invalid course ID format")

        course = await Course.get(course_id)
        if not course:
            raise ValueError("Course not found")

        # Collect question IDs
        question_ids: List[str] = [
            a["question_id"] for a in answers if a.get("question_id")
        ]
        if not question_ids:
            raise ValueError("No answers provided")

        # Convert string IDs to ObjectId for MongoDB query
        try:
            object_ids = [ObjectId(qid) for qid in question_ids]
        except Exception:
            raise ValueError("Invalid question ID format")

        # Fetch questions in bulk
        questions = await Question.find({"_id": {"$in": object_ids}}).to_list()

        # Index answers and questions
        answer_by_qid: Dict[str, Dict[str, Any]] = {
            a["question_id"]: a for a in answers
        }
        question_by_id: Dict[str, Question] = {}
        for q in questions:
            # Beanie id may be ObjectId; cast to str
            question_by_id[str(q.id)] = q

        # Scoring
        total_questions = len(questions)
        attempted = 0
        correct = 0
        per_section: Dict[str, Dict[str, int]] = {}
        question_results: List[Dict[str, Any]] = []

        for qid, q in question_by_id.items():
            ans = answer_by_qid.get(qid)
            if not ans:
                # unanswered
                section_name = getattr(q, "section", "General") or "General"
                per_section.setdefault(
                    section_name, {"total": 0, "attempted": 0, "correct": 0}
                )
                per_section[section_name]["total"] += 1
                question_results.append(
                    {
                        "question_id": qid,
                        "section": section_name,
                        "attempted": False,
                        "is_correct": False,
                        "selected_option_order": None,
                        "correct_option_order": next(
                            (o.order for o in q.options if o.is_correct), None
                        ),
                    }
                )
                continue

            section_name = getattr(q, "section", "General") or "General"
            per_section.setdefault(
                section_name, {"total": 0, "attempted": 0, "correct": 0}
            )
            per_section[section_name]["total"] += 1

            # Determine selected order
            selected_order = ans.get("selected_option_order")
            if selected_order is None and ans.get("selected_option_text") is not None:
                # Try to map by text (trim/normalize spaces)
                normalized = ans["selected_option_text"].strip()
                for opt in q.options:
                    if (opt.text or "").strip() == normalized:
                        selected_order = opt.order
                        break

            if selected_order is None:
                # treated as unanswered
                question_results.append(
                    {
                        "question_id": qid,
                        "section": section_name,
                        "attempted": False,
                        "is_correct": False,
                        "selected_option_order": None,
                        "correct_option_order": next(
                            (o.order for o in q.options if o.is_correct), None
                        ),
                    }
                )
                continue

            attempted += 1
            per_section[section_name]["attempted"] += 1

            correct_order = next((o.order for o in q.options if o.is_correct), None)
            is_correct = correct_order is not None and selected_order == correct_order
            if is_correct:
                correct += 1
                per_section[section_name]["correct"] += 1

            question_results.append(
                {
                    "question_id": qid,
                    "section": section_name,
                    "attempted": True,
                    "is_correct": is_correct,
                    "selected_option_order": selected_order,
                    "correct_option_order": correct_order,
                }
            )

        max_score = total_questions  # 1 mark per question for mock
        score = correct
        accuracy = (correct / attempted) if attempted > 0 else 0.0

        section_summaries = [
            {
                "section": name,
                "total": data["total"],
                "attempted": data["attempted"],
                "correct": data["correct"],
                "accuracy": (
                    (data["correct"] / data["attempted"])
                    if data["attempted"] > 0
                    else 0.0
                ),
            }
            for name, data in per_section.items()
        ]

        return {
            "message": "Mock submission scored successfully",
            "results": {
                "course": {
                    "id": str(course.id),
                    "title": course.title,
                    "code": course.code,
                },
                "user_id": str(current_user.id),
                "time_spent_seconds": time_spent_seconds or 0,
                "total_questions": total_questions,
                "attempted_questions": attempted,
                "correct_answers": correct,
                "score": score,
                "max_score": max_score,
                "percentage": (
                    round((score / max_score) * 100, 2) if max_score > 0 else 0
                ),
                "accuracy": round(accuracy, 4),
                "section_summaries": section_summaries,
                "question_results": question_results,
            },
        }
