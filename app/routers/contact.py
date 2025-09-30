from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from ..models.contact import Contact
from ..dependencies import ensure_db

router = APIRouter(prefix="/api/v1", tags=["contact"])


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: str
    message: str


@router.post("/contact", status_code=status.HTTP_201_CREATED)
async def submit_contact_form(contact_data: ContactForm):
    """Submit a contact form and store it in the database"""
    try:
        # Ensure database is available
        await ensure_db()

        # Create new contact entry
        contact = Contact(
            name=contact_data.name,
            email=contact_data.email,
            phone=contact_data.phone,
            message=contact_data.message,
        )

        # Save to database
        await contact.insert()

        return {
            "message": "Contact form submitted successfully",
            "contact_id": str(contact.id),
            "submitted_at": contact.created_at,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit contact form: {str(e)}",
        )


@router.get("/contact")
async def get_contact_submissions(skip: int = 0, limit: int = 50):
    """Get all contact form submissions (for admin use)"""
    try:
        # Ensure database is available
        await ensure_db()

        # Get contacts with pagination
        contacts = await Contact.find().skip(skip).limit(limit).to_list()

        # Convert to response format
        contact_list = []
        for contact in contacts:
            contact_list.append(
                {
                    "id": str(contact.id),
                    "name": contact.name,
                    "email": contact.email,
                    "phone": contact.phone,
                    "message": contact.message,
                    "created_at": contact.created_at,
                    "updated_at": contact.updated_at,
                }
            )

        return {
            "message": "Contact submissions retrieved successfully",
            "contacts": contact_list,
            "pagination": {"skip": skip, "limit": limit, "total": len(contact_list)},
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve contact submissions: {str(e)}",
        )
