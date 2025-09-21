"""
Admin image management endpoints for questions
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional, Dict, Any
from bson import ObjectId

from ...models.user import User
from ...models.question import Question
from ...dependencies import admin_required
from ...services.file_upload_service import FileUploadService
from ...services.admin_service import AdminService
from ...models.admin_action import ActionType

router = APIRouter(prefix="/images", tags=["Admin - Images"])


@router.post(
    "/upload",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Upload image for question",
    description="Upload image for question, option, explanation, or remarks",
)
async def upload_question_image(
    file: UploadFile = File(...),
    question_id: str = Form(...),
    image_type: str = Form(...),  # "question", "option", "explanation", "remarks"
    option_index: Optional[int] = Form(None),  # For option images
    current_user: User = Depends(admin_required),
):
    """
    Upload image for question components

    Args:
        file: Image file to upload
        question_id: ID of the question
        image_type: Type of image ("question", "option", "explanation", "remarks")
        option_index: Index of option (only for option images)
    """
    try:
        # Validate question_id
        if not ObjectId.is_valid(question_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid question ID format",
            )

        # Validate image_type
        valid_types = ["question", "option", "explanation", "remarks"]
        if image_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image_type. Must be one of: {', '.join(valid_types)}",
            )

        # For option images, option_index is required
        if image_type == "option" and option_index is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="option_index is required for option images",
            )

        # Get question
        question = await Question.get(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
            )

        # Upload image
        image_url = await FileUploadService.upload_question_image(
            file, question_id, image_type, option_index
        )

        # Update question with new image URL
        if image_type == "question":
            question.question_image_urls.append(image_url)
        elif image_type == "explanation":
            question.explanation_image_urls.append(image_url)
        elif image_type == "remarks":
            question.remarks_image_urls.append(image_url)
        elif image_type == "option" and option_index is not None:
            # Ensure we have enough options
            while len(question.options) <= option_index:
                from ...models.question import QuestionOption

                question.options.append(
                    QuestionOption(
                        text="", is_correct=False, order=len(question.options)
                    )
                )
            question.options[option_index].image_urls.append(image_url)

        # Save updated question
        await question.save()

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "questions",
            question_id,
            {
                "action": "image_uploaded",
                "image_type": image_type,
                "option_index": option_index,
                "image_url": image_url,
            },
        )

        return AdminService.format_response(
            "Image uploaded successfully",
            data={
                "image_url": image_url,
                "question_id": question_id,
                "image_type": image_type,
                "option_index": option_index,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )


@router.delete(
    "/delete",
    response_model=Dict[str, Any],
    summary="Delete image from question",
    description="Delete image from question, option, explanation, or remarks",
)
async def delete_question_image(
    question_id: str = Form(...),
    image_url: str = Form(...),
    image_type: str = Form(...),
    option_index: Optional[int] = Form(None),
    current_user: User = Depends(admin_required),
):
    """
    Delete image from question components

    Args:
        question_id: ID of the question
        image_url: URL of image to delete
        image_type: Type of image ("question", "option", "explanation", "remarks")
        option_index: Index of option (only for option images)
    """
    try:
        # Validate question_id
        if not ObjectId.is_valid(question_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid question ID format",
            )

        # Validate image_type
        valid_types = ["question", "option", "explanation", "remarks"]
        if image_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image_type. Must be one of: {', '.join(valid_types)}",
            )

        # Get question
        question = await Question.get(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
            )

        # Remove image URL from question
        image_removed = False
        if image_type == "question":
            if image_url in question.question_image_urls:
                question.question_image_urls.remove(image_url)
                image_removed = True
        elif image_type == "explanation":
            if image_url in question.explanation_image_urls:
                question.explanation_image_urls.remove(image_url)
                image_removed = True
        elif image_type == "remarks":
            if image_url in question.remarks_image_urls:
                question.remarks_image_urls.remove(image_url)
                image_removed = True
        elif image_type == "option" and option_index is not None:
            if (
                option_index < len(question.options)
                and image_url in question.options[option_index].image_urls
            ):
                question.options[option_index].image_urls.remove(image_url)
                image_removed = True

        if not image_removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found in question",
            )

        # Save updated question
        await question.save()

        # Delete image from storage
        await FileUploadService.delete_question_image(image_url)

        # Log admin action
        await AdminService.log_admin_action(
            str(current_user.id),
            ActionType.UPDATE,
            "questions",
            question_id,
            {
                "action": "image_deleted",
                "image_type": image_type,
                "option_index": option_index,
                "image_url": image_url,
            },
        )

        return AdminService.format_response(
            "Image deleted successfully",
            data={
                "question_id": question_id,
                "image_type": image_type,
                "option_index": option_index,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}",
        )


@router.get(
    "/{question_id}",
    response_model=Dict[str, Any],
    summary="Get question images",
    description="Get all images for a specific question",
)
async def get_question_images(
    question_id: str,
    current_user: User = Depends(admin_required),
):
    """
    Get all images for a question

    Args:
        question_id: ID of the question
    """
    try:
        # Validate question_id
        if not ObjectId.is_valid(question_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid question ID format",
            )

        # Get question
        question = await Question.get(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
            )

        # Prepare image data
        images = {
            "question_images": question.question_image_urls,
            "explanation_images": question.explanation_image_urls,
            "remarks_images": question.remarks_image_urls,
            "option_images": [],
        }

        # Add option images
        for i, option in enumerate(question.options):
            images["option_images"].append(
                {
                    "option_index": i,
                    "text": option.text,
                    "image_urls": option.image_urls,
                }
            )

        return AdminService.format_response(
            "Question images retrieved successfully",
            data={"question_id": question_id, "images": images},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get question images: {str(e)}",
        )
