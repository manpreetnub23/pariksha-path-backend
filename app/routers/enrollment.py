# app/routers/enrollment.py
from fastapi import APIRouter, Depends, HTTPException, status
from beanie import PydanticObjectId
from ..models.user import User
from ..models.course import Course
from ..auth import AuthService
from ..db import get_db_client

router = APIRouter(prefix="/api/v1/enroll", tags=["enrollment"])

@router.post("/{course_id}")
async def enroll_course(course_id: str, user: User = Depends(AuthService.get_current_user)):
    """
    Enroll the current user in the course.
    """
    try:
        # Fetch course
        course = await Course.get(PydanticObjectId(course_id))
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        # Enroll user if not already
        if course_id not in user.enrolled_courses:
            user.enrolled_courses.append(course_id)
            await user.save()

        return {"success": True, "message": f"Enrolled in {course.title}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
