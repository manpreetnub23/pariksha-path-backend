from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from typing import Optional, List, Dict, Any
from ..models.test import (
    TestSeries,
    TestSession,
    TestAttempt,
    create_test_session,
    get_test_with_attempt_stats,
)
from ..models.question import Question
from ..models.course import Course
from ..models.user import User
from ..models.enums import ExamCategory
from ..dependencies import get_current_user
from ..utils import (
    paginate_query,
    get_or_404,
    format_response,
    create_search_filter,
    add_filter_if_not_none,
)

router = APIRouter(prefix="/api/v1/tests", tags=["Tests"])


@router.get("/")
async def list_tests(
    category: Optional[ExamCategory] = Query(
        None, description="Filter by exam category"
    ),
    subcategory: Optional[str] = Query(None, description="Filter by exam subcategory"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    is_free: Optional[bool] = Query(None, description="Filter by free/paid status"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List available tests with filtering and pagination.

    Tests can be filtered by various criteria and paginated.
    Results include information about user's access to each test.
    """
    try:
        # Build query filters
        query_filters = {"is_active": True}

        # Add filters if provided
        add_filter_if_not_none(query_filters, "exam_category", category)
        add_filter_if_not_none(query_filters, "exam_subcategory", subcategory)
        add_filter_if_not_none(query_filters, "difficulty", difficulty)
        add_filter_if_not_none(query_filters, "is_free", is_free)

        # Add text search if provided
        if search:
            search_filter = create_search_filter(search, ["title", "description"])
            if search_filter:
                query_filters.update(search_filter)

        # Filter by course if provided
        if course_id:
            course = await get_or_404(Course, course_id, detail="Course not found")
            query_filters["_id"] = {"$in": course.test_series_ids}

        # Transform function for test items
        async def transform_test(test):
            # Determine if user has access
            has_access = test.is_free or current_user.has_premium_access

            # Check if user purchased this test
            if not has_access and str(test.id) in current_user.purchased_test_series:
                has_access = True

            # Check if user is enrolled in a course with this test
            if not has_access:
                for enrolled_course_id in current_user.enrolled_courses:
                    course = await Course.get(enrolled_course_id)
                    if course and str(test.id) in course.test_series_ids:
                        has_access = True
                        break

            # Get user's attempt stats for this test
            test_data = await get_test_with_attempt_stats(str(test.id), current_user.id)
            test_data["has_access"] = has_access

            return test_data

        # Use pagination utility
        tests, pagination = await paginate_query(
            TestSeries, query_filters, sort_by, sort_order, page, limit, transform_test
        )

        return format_response(
            message="Tests retrieved successfully", data=tests, pagination=pagination
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tests: {str(e)}",
        )


@router.get("/{test_id}")
async def get_test(
    test_id: str = Path(..., description="Test ID"),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific test.

    Returns test details and user's attempt statistics if available.
    """
    try:
        # Get test or raise 404
        test = await get_or_404(TestSeries, test_id, detail="Test not found")

        # Check if test is active
        if not test.is_active and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test not found or inactive",
            )

        # Get test with user's attempt stats
        test_data = await get_test_with_attempt_stats(test_id, current_user.id)

        # Determine if user has access
        has_access = test.is_free or current_user.has_premium_access

        # Check if user purchased this test
        if not has_access and str(test.id) in current_user.purchased_test_series:
            has_access = True

        # Check if user is enrolled in a course with this test
        if not has_access:
            for course_id in current_user.enrolled_courses:
                course = await Course.get(course_id)
                if course and str(test.id) in course.test_series_ids:
                    has_access = True
                    break

        test_data["has_access"] = has_access

        # If admin, include additional details
        if current_user.role == "admin":
            test_data["created_by"] = test.created_by
            test_data["question_ids"] = test.question_ids
            test_data["sections"] = [section.dict() for section in test.sections]

        return format_response(message="Test retrieved successfully", data=test_data)

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test: {str(e)}",
        )


@router.post("/{test_id}/start")
async def start_test(
    test_id: str = Path(..., description="Test ID"),
    current_user: User = Depends(get_current_user),
):
    """
    Start a new test session.

    Creates a new test session and attempt for the specified test.
    Returns session details needed to take the test.
    """
    try:
        # Get test or raise 404
        test = await get_or_404(TestSeries, test_id, detail="Test not found")

        # Check if test is active
        if not test.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This test is not currently available",
            )

        # Determine if user has access
        has_access = test.is_free or current_user.has_premium_access

        # Check if user purchased this test
        if not has_access and str(test.id) in current_user.purchased_test_series:
            has_access = True

        # Check if user is enrolled in a course with this test
        if not has_access:
            for course_id in current_user.enrolled_courses:
                course = await Course.get(course_id)
                if course and str(test.id) in course.test_series_ids:
                    has_access = True
                    break

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this test",
            )

        # Check if user already has an active session for this test
        existing_session = await TestSession.find_one(
            {"user_id": current_user.id, "test_series_id": test_id, "is_active": True}
        )

        if existing_session:
            # Return existing session
            return format_response(
                message="Resuming existing test session",
                data={
                    "session_id": str(existing_session.id),
                    "attempt_id": existing_session.attempt_id,
                    "remaining_time": existing_session.calculate_remaining_time(),
                    "current_question": existing_session.current_question_index,
                    "is_new_session": False,
                },
            )

        # Create new session and attempt
        session, attempt = await create_test_session(current_user.id, test_id)

        return format_response(
            message="Test session started successfully",
            data={
                "session_id": str(session.id),
                "attempt_id": str(attempt.id),
                "remaining_time": session.calculate_remaining_time(),
                "current_question": 0,
                "is_new_session": True,
                "test_info": {
                    "title": test.title,
                    "total_questions": test.total_questions,
                    "duration_minutes": test.duration_minutes,
                    "max_score": test.max_score,
                },
            },
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start test: {str(e)}",
        )


@router.get("/attempts")
async def list_test_attempts(
    test_id: Optional[str] = Query(None, description="Filter by test ID"),
    is_completed: Optional[bool] = Query(
        None, description="Filter by completion status"
    ),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, description="Page number", ge=1),
    limit: int = Query(10, description="Items per page", ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    List user's test attempts with filtering and pagination.

    Returns a list of the user's attempts at various tests.
    """
    try:
        # Build query filters
        query_filters = {"user_id": current_user.id}

        # Add filters if provided
        add_filter_if_not_none(query_filters, "test_series_id", test_id)
        add_filter_if_not_none(query_filters, "is_completed", is_completed)

        # Transform function for attempt items
        async def transform_attempt(attempt):
            # Get test info
            test = await TestSeries.get(attempt.test_series_id)
            test_title = test.title if test else "Unknown Test"

            return {
                "id": str(attempt.id),
                "test_id": attempt.test_series_id,
                "test_title": test_title,
                "start_time": attempt.start_time,
                "end_time": attempt.end_time,
                "score": attempt.score,
                "max_score": attempt.max_score,
                "percentage": (
                    round((attempt.score / attempt.max_score) * 100, 2)
                    if attempt.max_score > 0
                    else 0
                ),
                "is_completed": attempt.is_completed,
                "passed": attempt.passed,
                "total_questions": attempt.total_questions,
                "attempted_questions": attempt.attempted_questions,
                "correct_answers": attempt.correct_answers,
                "accuracy": attempt.accuracy,
            }

        # Use pagination utility
        attempts, pagination = await paginate_query(
            TestAttempt,
            query_filters,
            sort_by,
            sort_order,
            page,
            limit,
            transform_attempt,
        )

        return format_response(
            message="Test attempts retrieved successfully",
            data=attempts,
            pagination=pagination,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test attempts: {str(e)}",
        )


@router.get("/attempts/{attempt_id}")
async def get_test_attempt(
    attempt_id: str = Path(..., description="Attempt ID"),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific test attempt.

    Returns comprehensive performance data for a completed test attempt.
    """
    try:
        # Get attempt or raise 404
        attempt = await get_or_404(
            TestAttempt, attempt_id, detail="Test attempt not found"
        )

        # Check if attempt belongs to user or user is admin
        if attempt.user_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this test attempt",
            )

        # Get test info
        test = await get_or_404(
            TestSeries, attempt.test_series_id, detail="Test not found"
        )

        # Format response data
        attempt_data = {
            "id": str(attempt.id),
            "test_id": attempt.test_series_id,
            "test_title": test.title,
            "start_time": attempt.start_time,
            "end_time": attempt.end_time,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "percentage": (
                round((attempt.score / attempt.max_score) * 100, 2)
                if attempt.max_score > 0
                else 0
            ),
            "is_completed": attempt.is_completed,
            "passed": attempt.passed,
            "total_questions": attempt.total_questions,
            "attempted_questions": attempt.attempted_questions,
            "correct_answers": attempt.correct_answers,
            "accuracy": attempt.accuracy,
            "time_spent_seconds": attempt.time_spent_seconds,
            # Include detailed analytics if attempt is completed
            "section_summaries": (
                [section.dict() for section in attempt.section_summaries]
                if attempt.is_completed
                else []
            ),
            "subject_wise_performance": (
                attempt.subject_wise_performance if attempt.is_completed else {}
            ),
            "topic_wise_performance": (
                attempt.topic_wise_performance if attempt.is_completed else {}
            ),
            "strengths": attempt.strengths if attempt.is_completed else [],
            "weaknesses": attempt.weaknesses if attempt.is_completed else [],
        }

        # Include question attempts if attempt is completed
        if attempt.is_completed:
            attempt_data["question_attempts"] = [
                q.dict() for q in attempt.question_attempts
            ]

        return format_response(
            message="Test attempt retrieved successfully", data=attempt_data
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test attempt: {str(e)}",
        )


@router.get("/{test_id}/questions")
async def get_test_questions(
    test_id: str,
    current_user: User = Depends(get_current_user),
):
    test = await get_or_404(TestSeries, test_id, detail="Test not found")

    if not test.is_active:
        raise HTTPException(status_code=404, detail="Test not active")

    # Fetch questions by IDs
    questions = []
    for qid in test.question_ids:
        question = await Question.get(qid)
        if question:
            questions.append(question)

    return format_response(
        message="Questions retrieved successfully",
        data=[q.dict() for q in questions]
    )