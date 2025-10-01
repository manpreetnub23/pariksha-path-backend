import os, hmac, hashlib, time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import razorpay
from ..dependencies import get_current_user  # 👈 apna existing auth service
from ..models.user import User
from ..config import settings
from ..utils import deterministic_receipt_hex12


router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET

# Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ---------- Schemas ----------
class CreateOrderRequest(BaseModel):
    amount: int  # in paise
    currency: str = "INR"
    course_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    course_id: str


# ---------- Routes ----------
@router.post("/create-order")
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),  # 👈 same as other routes
):
    try:
        print(current_user)
        order = razorpay_client.order.create(
            {
                "amount": request.amount,
                "currency": request.currency,
                "receipt": deterministic_receipt_hex12(
                    request.course_id, str(current_user.id)
                ),
                "payment_capture": 1,
            }
        )
        print("heelo gurrakha")
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),  # 👈 same here
):
    try:
        body = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            bytes(RAZORPAY_KEY_SECRET, "utf-8"),
            bytes(body, "utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if expected_signature != request.razorpay_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature",
            )

        # ✅ Payment verified, enroll user in course
        if request.course_id not in current_user.enrolled_courses:
            current_user.enrolled_courses.append(request.course_id)
            await current_user.save()

        return {"success": True, "message": "Enrolled successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-data")
async def get_user_data(
    current_user: User = Depends(get_current_user),  # 👈 same here
):
    try:
        return {
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
