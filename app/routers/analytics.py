from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional, Dict, Any

from ..models.user import User
from ..models.user_analytics import UserAnalytics, PerformanceLevel
from ..models.dashboard_analytics import AdminDashboardMetrics, ExamCategoryAnalytics
from ..models.test import TestAttempt, TestSeries
from ..models.course import Course
from ..models.enums import ExamCategory, UserRole
from ..models.study_material import StudyMaterial
from ..dependencies import admin_required, get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


# User Analytics Endpoints


@router.get("/user")
async def get_user_analytics(current_user: User = Depends(get_current_user)):
    """Get current user's performance analytics"""
    try:
        # Get user analytics or create if not exists
        analytics = await UserAnalytics.find_one({"user_id": str(current_user.id)})
        if not analytics:
            analytics = UserAnalytics(user_id=str(current_user.id))
            await analytics.insert()

        # Get recent test attempts
        recent_attempts = (
            await TestAttempt.find(
                {"user_id": str(current_user.id), "is_completed": True}
            )
            .sort([("created_at", -1)])
            .limit(5)
            .to_list()
        )

        # Format recent attempts
        recent_attempts_data = []
        for attempt in recent_attempts:
            test = await TestSeries.get(attempt.test_series_id)
            if test:
                recent_attempts_data.append(
                    {
                        "id": str(attempt.id),
                        "test_id": str(test.id),
                        "test_title": test.title,
                        "score": attempt.score,
                        "max_score": attempt.max_score,
                        "percentage": (
                            round((attempt.score / attempt.max_score) * 100, 2)
                            if attempt.max_score > 0
                            else 0
                        ),
                        "accuracy": attempt.accuracy,
                        "date": attempt.created_at,
                    }
                )

        # Get subject performance overview
        subject_performance = analytics.subject_performance

        # Calculate overall progress and improvement
        progress = {
            "tests_completed": analytics.tests_taken,
            "avg_score": analytics.avg_test_score,
            "avg_percentile": analytics.avg_percentile,
            "best_percentile": analytics.best_percentile,
            "study_time_minutes": analytics.total_study_time_minutes,
            "improvement": _calculate_improvement(recent_attempts),
            "exam_readiness": analytics.exam_readiness,
        }

        # Format strengths and weaknesses
        strengths = [
            {"subject": subject, "accuracy": data.get("accuracy", 0)}
            for subject, data in subject_performance.items()
            if data.get("accuracy", 0) >= 0.7
        ]

        weaknesses = [
            {"subject": subject, "accuracy": data.get("accuracy", 0)}
            for subject, data in subject_performance.items()
            if data.get("accuracy", 0) < 0.5 and data.get("attempts", 0) > 0
        ]

        # Format study habits
        study_habits = analytics.study_habits.dict() if analytics.study_habits else {}

        return {
            "message": "User analytics retrieved successfully",
            "data": {
                "overall_progress": progress,
                "recent_attempts": recent_attempts_data,
                "subject_performance": subject_performance,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "study_habits": study_habits,
                "exam_readiness": analytics.exam_readiness,
                "performance_timeline": analytics.performance_timeline,
                "materials_stats": {
                    "accessed": analytics.materials_accessed,
                    "completed": analytics.materials_completed,
                },
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user analytics: {str(e)}",
        )


@router.get("/tests/{test_id}")
async def get_test_analytics(
    test_id: str, current_user: User = Depends(get_current_user)
):
    """Get analytics for a specific test"""
    try:
        # Check if test exists
        test = await TestSeries.get(test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Test not found"
            )

        # Get user's attempts for this test
        user_attempts = (
            await TestAttempt.find(
                {
                    "user_id": str(current_user.id),
                    "test_series_id": test_id,
                    "is_completed": True,
                }
            )
            .sort([("created_at", -1)])
            .to_list()
        )

        # Get all attempts for this test (for percentile calculation)
        all_attempts = await TestAttempt.find(
            {"test_series_id": test_id, "is_completed": True}
        ).to_list()

        # Calculate user's percentile
        user_percentile = 0
        if user_attempts and all_attempts:
            best_attempt = max(user_attempts, key=lambda x: x.score)
            better_than = sum(1 for a in all_attempts if a.score < best_attempt.score)
            user_percentile = round((better_than / len(all_attempts)) * 100, 2)

        # Get latest attempt details
        latest_attempt = user_attempts[0] if user_attempts else None
        attempt_details = None

        if latest_attempt:
            # Process attempt details
            attempt_details = {
                "id": str(latest_attempt.id),
                "score": latest_attempt.score,
                "max_score": latest_attempt.max_score,
                "percentage": (
                    round((latest_attempt.score / latest_attempt.max_score) * 100, 2)
                    if latest_attempt.max_score > 0
                    else 0
                ),
                "accuracy": latest_attempt.accuracy,
                "time_spent_seconds": latest_attempt.time_spent_seconds,
                "date": latest_attempt.created_at,
                "percentile": user_percentile,
                "subject_wise_performance": latest_attempt.subject_wise_performance,
                "topic_wise_performance": latest_attempt.topic_wise_performance,
            }

            # Add section summaries if available
            if latest_attempt.section_summaries:
                attempt_details["section_summaries"] = [
                    section.dict() for section in latest_attempt.section_summaries
                ]

        # Get performance trend over time
        performance_trend = []
        for attempt in sorted(user_attempts, key=lambda x: x.created_at):
            performance_trend.append(
                {
                    "date": attempt.created_at,
                    "score_percentage": (
                        round((attempt.score / attempt.max_score) * 100, 2)
                        if attempt.max_score > 0
                        else 0
                    ),
                    "accuracy": attempt.accuracy,
                }
            )

        # Get class average
        class_average = 0
        if all_attempts:
            class_average = (
                sum(a.score / a.max_score for a in all_attempts if a.max_score > 0)
                / len(all_attempts)
                * 100
            )
            class_average = round(class_average, 2)

        return {
            "message": "Test analytics retrieved successfully",
            "data": {
                "test_info": {
                    "id": str(test.id),
                    "title": test.title,
                    "total_questions": test.total_questions,
                    "difficulty": test.difficulty,
                    "class_average": class_average,
                    "attempt_count": test.attempt_count,
                },
                "user_performance": {
                    "attempts_count": len(user_attempts),
                    "latest_attempt": attempt_details,
                    "percentile": user_percentile,
                    "performance_trend": performance_trend,
                },
                "recommendations": (
                    _generate_recommendations(latest_attempt) if latest_attempt else []
                ),
            },
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve test analytics: {str(e)}",
        )


# Admin Analytics Endpoints


@router.get("/admin/dashboard")
async def get_admin_dashboard_analytics(current_user: User = Depends(admin_required)):
    """Get comprehensive analytics for admin dashboard"""
    try:
        # Get or create dashboard metrics
        metrics = await AdminDashboardMetrics.find_one({}) or AdminDashboardMetrics()

        # Calculate fresh metrics

        # User metrics
        total_users = await User.find({"role": UserRole.STUDENT}).count()
        active_users = await User.find(
            {"role": UserRole.STUDENT, "is_active": True}
        ).count()

        # Get users registered today
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        users_today = await User.find(
            {"role": UserRole.STUDENT, "created_at": {"$gte": today_start}}
        ).count()

        # Get users registered this week
        week_start = today_start - timedelta(days=today_start.weekday())
        users_this_week = await User.find(
            {"role": UserRole.STUDENT, "created_at": {"$gte": week_start}}
        ).count()

        # Get users registered this month
        month_start = today_start.replace(day=1)
        users_this_month = await User.find(
            {"role": UserRole.STUDENT, "created_at": {"$gte": month_start}}
        ).count()

        # Course metrics
        total_courses = await Course.find().count()
        active_courses = await Course.find({"is_active": True}).count()

        # Test metrics
        total_tests = await TestSeries.find().count()
        active_tests = await TestSeries.find({"is_active": True}).count()
        total_attempts = await TestAttempt.find().count()

        # Recent test attempts
        recent_attempts = (
            await TestAttempt.find().sort([("created_at", -1)]).limit(10).to_list()
        )
        recent_attempts_data = []

        for attempt in recent_attempts:
            user = await User.get(attempt.user_id)
            test = await TestSeries.get(attempt.test_series_id)

            if user and test:
                recent_attempts_data.append(
                    {
                        "id": str(attempt.id),
                        "user_id": str(user.id),
                        "user_name": user.name,
                        "test_id": str(test.id),
                        "test_title": test.title,
                        "score": attempt.score,
                        "max_score": attempt.max_score,
                        "percentage": (
                            round((attempt.score / attempt.max_score) * 100, 2)
                            if attempt.max_score > 0
                            else 0
                        ),
                        "date": attempt.created_at,
                    }
                )

        # Study material metrics
        total_materials = await StudyMaterial.find().count()
        active_materials = await StudyMaterial.find({"is_active": True}).count()

        # Exam category distribution
        category_distribution = {}
        for category in ExamCategory:
            count = await User.find({"preferred_exam_categories": category}).count()
            category_distribution[category.value] = count

        # Daily signups for the last 30 days
        daily_signups = []
        for i in range(30, -1, -1):
            date = today_start - timedelta(days=i)
            next_date = date + timedelta(days=1)

            count = await User.find(
                {
                    "role": UserRole.STUDENT,
                    "created_at": {"$gte": date, "$lt": next_date},
                }
            ).count()

            daily_signups.append({"date": date.strftime("%Y-%m-%d"), "count": count})

        # Daily test attempts for the last 30 days
        daily_attempts = []
        for i in range(30, -1, -1):
            date = today_start - timedelta(days=i)
            next_date = date + timedelta(days=1)

            count = await TestAttempt.find(
                {"created_at": {"$gte": date, "$lt": next_date}}
            ).count()

            daily_attempts.append({"date": date.strftime("%Y-%m-%d"), "count": count})

        # Popular tests
        popular_tests = []
        all_tests = (
            await TestSeries.find().sort([("attempt_count", -1)]).limit(5).to_list()
        )
        for test in all_tests:
            popular_tests.append(
                {
                    "id": str(test.id),
                    "title": test.title,
                    "attempts": test.attempt_count,
                    "avg_score": test.avg_score,
                }
            )

        # Format response
        dashboard_data = {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "today": users_today,
                "this_week": users_this_week,
                "this_month": users_this_month,
            },
            "courses": {
                "total": total_courses,
                "active": active_courses,
                "inactive": total_courses - active_courses,
            },
            "tests": {
                "total": total_tests,
                "active": active_tests,
                "attempts": total_attempts,
                "popular": popular_tests,
                "recent_attempts": recent_attempts_data,
            },
            "materials": {"total": total_materials, "active": active_materials},
            "exam_categories": category_distribution,
            "trends": {
                "daily_signups": daily_signups,
                "daily_test_attempts": daily_attempts,
            },
        }

        # Update stored metrics
        metrics.total_users = total_users
        metrics.active_users = active_users
        metrics.new_users_today = users_today
        metrics.new_users_this_week = users_this_week
        metrics.new_users_this_month = users_this_month
        metrics.daily_signups = daily_signups
        metrics.daily_test_attempts = daily_attempts
        metrics.last_updated = datetime.now(timezone.utc)
        await metrics.save()

        return {
            "message": "Admin dashboard analytics retrieved successfully",
            "data": dashboard_data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve admin dashboard analytics: {str(e)}",
        )


@router.get("/admin/exam-categories/{category}")
async def get_exam_category_analytics(
    category: ExamCategory, current_user: User = Depends(admin_required)
):
    """Get analytics for a specific exam category"""
    try:
        # Get or create category analytics
        category_analytics = await ExamCategoryAnalytics.find_one(
            {"category": category.value}
        )
        if not category_analytics:
            category_analytics = ExamCategoryAnalytics(category=category.value)

        # Calculate metrics

        # User metrics for this category
        total_users = await User.find({"preferred_exam_categories": category}).count()

        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        active_users = await User.find(
            {
                "preferred_exam_categories": category,
                "last_login": {"$gte": thirty_days_ago},
            }
        ).count()

        # Test metrics
        category_tests = await TestSeries.find(
            {"exam_category": category.value}
        ).to_list()
        test_ids = [str(test.id) for test in category_tests]

        # Test attempts for this category
        attempts = await TestAttempt.find(
            {"test_series_id": {"$in": test_ids}, "is_completed": True}
        ).to_list()

        # Calculate average score
        avg_score = 0
        if attempts:
            avg_score = (
                sum(a.score / a.max_score for a in attempts if a.max_score > 0)
                / len(attempts)
                * 100
            )
            avg_score = round(avg_score, 2)

        # Popular tests in this category
        popular_tests = []
        for test in sorted(category_tests, key=lambda x: x.attempt_count, reverse=True)[
            :5
        ]:
            popular_tests.append(
                {
                    "id": str(test.id),
                    "title": test.title,
                    "attempts": test.attempt_count,
                    "avg_score": test.avg_score,
                }
            )

        # Materials for this category
        materials = await StudyMaterial.find(
            {"exam_category": category.value}
        ).to_list()

        # Popular materials
        popular_materials = []
        for material in sorted(materials, key=lambda x: x.download_count, reverse=True)[
            :5
        ]:
            popular_materials.append(
                {
                    "id": str(material.id),
                    "title": material.title,
                    "downloads": material.download_count,
                    "views": material.view_count,
                }
            )

        # Score distribution
        score_distribution = {
            "0-10%": 0,
            "10-20%": 0,
            "20-30%": 0,
            "30-40%": 0,
            "40-50%": 0,
            "50-60%": 0,
            "60-70%": 0,
            "70-80%": 0,
            "80-90%": 0,
            "90-100%": 0,
        }

        for attempt in attempts:
            percentage = (
                (attempt.score / attempt.max_score) * 100
                if attempt.max_score > 0
                else 0
            )
            if percentage < 10:
                score_distribution["0-10%"] += 1
            elif percentage < 20:
                score_distribution["10-20%"] += 1
            elif percentage < 30:
                score_distribution["20-30%"] += 1
            elif percentage < 40:
                score_distribution["30-40%"] += 1
            elif percentage < 50:
                score_distribution["40-50%"] += 1
            elif percentage < 60:
                score_distribution["50-60%"] += 1
            elif percentage < 70:
                score_distribution["60-70%"] += 1
            elif percentage < 80:
                score_distribution["70-80%"] += 1
            elif percentage < 90:
                score_distribution["80-90%"] += 1
            else:
                score_distribution["90-100%"] += 1

        # Update category analytics
        category_analytics.total_enrolled_users = total_users
        category_analytics.active_users_30d = active_users
        category_analytics.avg_test_score = avg_score
        category_analytics.top_tests = popular_tests
        category_analytics.top_materials = popular_materials
        category_analytics.score_distribution = score_distribution
        category_analytics.last_updated = datetime.now(timezone.utc)
        await category_analytics.save()

        return {
            "message": f"Analytics for {category.value} retrieved successfully",
            "data": {
                "category": category.value,
                "users": {
                    "total_enrolled": total_users,
                    "active_users_30d": active_users,
                },
                "tests": {
                    "total_count": len(category_tests),
                    "total_attempts": len(attempts),
                    "avg_score": avg_score,
                    "popular_tests": popular_tests,
                },
                "materials": {
                    "total_count": len(materials),
                    "popular_materials": popular_materials,
                },
                "score_distribution": score_distribution,
                "last_updated": category_analytics.last_updated,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve exam category analytics: {str(e)}",
        )


# Helper functions


def _calculate_improvement(recent_attempts: List[TestAttempt]) -> Dict[str, Any]:
    """Calculate user's improvement over time based on recent attempts"""
    if len(recent_attempts) < 2:
        return {"trend": "neutral", "percentage": 0}

    # Sort by date
    sorted_attempts = sorted(recent_attempts, key=lambda x: x.created_at)

    # Calculate average scores for first half and second half
    mid_point = len(sorted_attempts) // 2
    first_half = sorted_attempts[:mid_point]
    second_half = sorted_attempts[mid_point:]

    first_half_avg = (
        sum(a.score / a.max_score for a in first_half if a.max_score > 0)
        / len(first_half)
        if first_half
        else 0
    )
    second_half_avg = (
        sum(a.score / a.max_score for a in second_half if a.max_score > 0)
        / len(second_half)
        if second_half
        else 0
    )

    # Calculate improvement
    improvement = second_half_avg - first_half_avg
    percentage = round(improvement * 100, 1)

    if improvement > 0.05:  # 5% improvement
        trend = "improving"
    elif improvement < -0.05:  # 5% decline
        trend = "declining"
    else:
        trend = "stable"

    return {"trend": trend, "percentage": percentage}


def _generate_recommendations(attempt: TestAttempt) -> List[str]:
    """Generate study recommendations based on test performance"""
    recommendations = []

    if not attempt:
        return recommendations

    # Add recommendations based on weak subjects
    weak_subjects = []
    for subject, data in attempt.subject_wise_performance.items():
        score_percentage = data.get("score", 0) / data.get("max", 1) * 100
        if score_percentage < 40:
            weak_subjects.append(subject)
            recommendations.append(
                f"Focus on improving {subject} - you scored below 40%"
            )

    # Add recommendations based on weak topics
    weak_topics = []
    for topic, data in attempt.topic_wise_performance.items():
        score_percentage = data.get("score", 0) / data.get("max", 1) * 100
        if score_percentage < 30:
            weak_topics.append(topic)
            if len(recommendations) < 5:  # Limit recommendations
                recommendations.append(
                    f"Review the topic {topic} where you scored below 30%"
                )

    # Add general recommendations
    if attempt.accuracy < 0.5:
        recommendations.append(
            "Work on improving accuracy - you're attempting questions but getting many wrong"
        )

    if attempt.attempted_questions / attempt.total_questions < 0.8:
        recommendations.append(
            "Try to attempt more questions - you left many unanswered"
        )

    return recommendations[:5]  # Limit to top 5 recommendations
