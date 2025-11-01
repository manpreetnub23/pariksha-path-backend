"""
Mock test service for course-based mock testing functionality
"""

from typing import Dict, Any, List, Optional
from bson import ObjectId

from ..models.course import Course
from ..models.question import Question
from ..models.user import User
from ..models.test import TestAttempt, QuestionAttempt, SectionSummary
from datetime import datetime, timezone, timedelta


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

        # Validate that time spent doesn't exceed course timer limit
        max_time_seconds = course.mock_test_timer_seconds
        if time_spent_seconds > max_time_seconds:
            print(f"WARNING: Reported time spent ({time_spent_seconds}s) exceeds course timer limit ({max_time_seconds}s)")
            # Cap the time spent to the course limit
            time_spent_seconds = max_time_seconds

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
        total_negative_deductions: float = 0.0
        total_marks_available: float = 0.0
        score_total: float = 0.0

        for qid, q in question_by_id.items():
            ans = answer_by_qid.get(qid)
            # Per-question marks available
            q_marks = 0.0
            try:
                q_marks = float(getattr(q, "marks", 1.0) or 1.0)
            except Exception:
                q_marks = 1.0
            total_marks_available += q_marks

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
                        "negative_deduction": 0.0,
                        "marks_available": q_marks,
                        "marks_awarded": 0.0,
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

            # Handle selected_options array format (from frontend)
            if selected_order is None and ans.get("selected_options"):
                selected_options = ans["selected_options"]
                if isinstance(selected_options, list) and len(selected_options) > 0:
                    selected_order = selected_options[0]  # Take first answer from array
                    print(f"DEBUG: Using selected_options[0] = {selected_order} for question {qid}")

            if selected_order is None and ans.get("selected_option_text") is not None:
                # Try to map by text (trim/normalize spaces)
                normalized = ans["selected_option_text"].strip()
                for opt in q.options:
                    if (opt.text or "").strip() == normalized:
                        selected_order = opt.order
                        break

            print(f"DEBUG: Question {qid}: selected_order={selected_order}, correct_order will be calculated")

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

            print(f"DEBUG: Question {qid}: selected_order={selected_order}, correct_order={correct_order}, is_correct={is_correct}")

            if is_correct:
                correct += 1
                per_section[section_name]["correct"] += 1
                score_total += q_marks

            # Determine negative deduction for incorrect attempted questions
            neg_val = 0.0
            if not is_correct and selected_order is not None:
                try:
                    meta = getattr(q, "metadata", {}) or {}
                    raw = meta.get("negative_marks", 0)
                    neg = float(raw) if raw is not None else 0.0
                    if neg < 0:
                        neg = 0.0
                    neg_val = neg
                except Exception:
                    neg_val = 0.0
                total_negative_deductions += neg_val
                score_total -= neg_val

            question_results.append(
                {
                    "question_id": qid,
                    "section": section_name,
                    "attempted": True,
                    "is_correct": is_correct,
                    "selected_option_order": selected_order,
                    "correct_option_order": correct_order,
                    "negative_deduction": neg_val,
                    "marks_available": q_marks,
                    "marks_awarded": (q_marks if is_correct else 0.0),
                }
            )

        max_score = float(total_marks_available)  # sum of marks per question
        score = float(score_total)  # may be negative
        accuracy = (correct / attempted) if attempted > 0 else 0.0

        print(f"DEBUG: Final stats - total_questions={total_questions}, attempted={attempted}, correct={correct}, score={score}, max_score={max_score}, accuracy={accuracy}")

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

        # Create question attempts for the TestAttempt model
        question_attempts = []
        for qr in question_results:
            # Create QuestionAttempt using the correct fields according to the model
            question_attempt = QuestionAttempt(
                question_id=qr["question_id"],
                # Convert to the expected format
                selected_options=(
                    [str(qr["selected_option_order"])]
                    if qr["selected_option_order"] is not None
                    else []
                ),
                # Map to the correct AnswerStatus enum value
                status=(
                    "correct"
                    if qr["is_correct"]
                    else "incorrect" if qr["attempted"] else "skipped"
                ),
                marks_awarded=float(qr.get("marks_awarded", 0.0)),
                marks_available=float(qr.get("marks_available", 1.0)),
                negative_marks=float(qr.get("negative_deduction", 0.0)),
                time_spent_seconds=0,  # We don't track per-question time
            )
            question_attempts.append(question_attempt)

        # Create section summaries for the TestAttempt model
        section_summary_objects = []
        for summary in section_summaries:
            section_summary = SectionSummary(
                section_name=summary["section"],
                total_questions=summary["total"],
                attempted_questions=summary["attempted"],
                correct_answers=summary["correct"],
                marks_obtained=summary["correct"],  # 1 mark per correct answer
                max_marks=summary["total"],  # 1 mark per question
                accuracy_percent=summary["accuracy"] * 100,  # Convert to percentage
            )
            section_summary_objects.append(section_summary)

        # Create and save the TestAttempt
        test_attempt = TestAttempt(
            user_id=str(current_user.id),
            test_series_id=course_id,  # Using course_id as test_series_id for mock tests
            start_time=datetime.now(timezone.utc)
            - timedelta(seconds=time_spent_seconds or 0),
            end_time=datetime.now(timezone.utc),
            question_attempts=question_attempts,
            section_summaries=section_summary_objects,
            total_questions=total_questions,
            attempted_questions=attempted,
            correct_answers=correct,
            score=score,
            max_score=max_score,
            accuracy=accuracy,
            time_spent_seconds=time_spent_seconds or 0,
            is_completed=True,
        )

        # Save the test attempt to the database
        await test_attempt.insert()

        result = {
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
                    max(0.0, round((score / max_score) * 100, 2)) if max_score > 0 else 0
                ),
                "accuracy": round(accuracy, 4),
                "section_summaries": section_summaries,
                "question_results": question_results,
                "negative_deductions": round(float(total_negative_deductions), 4),
                "attempt_id": str(test_attempt.id),
            },
        }

        print(f"DEBUG: Final result - score={result['results']['score']}, percentage={result['results']['percentage']}, accuracy={result['results']['accuracy']}")

        return result
