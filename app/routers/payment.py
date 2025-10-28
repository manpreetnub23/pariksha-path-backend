import os, hmac, hashlib, time, logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import razorpay
from ..dependencies import get_current_user  # 👈 apna existing auth service
from ..models.user import User
from ..config import settings
from ..utils import deterministic_receipt_hex12

# Set up logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

# Log the keys being used (redacted for security)
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
    logger.info(f"[CREATE ORDER] Starting order creation for user: {current_user.email}, course_id: {request.course_id}")
    logger.info(f"[CREATE ORDER] Request amount: {request.amount} paise, currency: {request.currency}")

    try:
        # Validate amount
        if request.amount <= 0:
            logger.error(f"[CREATE ORDER] Invalid amount: {request.amount}")
            raise HTTPException(status_code=400, detail="Amount must be greater than 0")

        # Create receipt
        receipt = deterministic_receipt_hex12(request.course_id, str(current_user.id))
        logger.info(f"[CREATE ORDER] Generated receipt: {receipt}")

        # Razorpay order data
        order_data = {
            "amount": request.amount,
            "currency": request.currency,
            "receipt": receipt,
            "payment_capture": 1,
        }
        logger.info(f"[CREATE ORDER] Sending to Razorpay: {order_data}")

        # Create order with Razorpay
        order = razorpay_client.order.create(order_data)
        logger.info(f"[CREATE ORDER] Razorpay response: {order}")

        # Validate order response
        if not order or 'id' not in order:
            logger.error(f"[CREATE ORDER] Invalid order response from Razorpay: {order}")
            raise HTTPException(status_code=500, detail="Failed to create order with payment gateway")

        logger.info(f"[CREATE ORDER] Order created successfully: {order['id']}")
        return order

    except razorpay.errors.BadRequestError as e:
        logger.error(f"[CREATE ORDER] Razorpay BadRequestError: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment gateway error: {str(e)}")
    except razorpay.errors.ServerError as e:
        logger.error(f"[CREATE ORDER] Razorpay ServerError: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment gateway server error: {str(e)}")
    except razorpay.errors.AuthenticationError as e:
        logger.error(f"[CREATE ORDER] Razorpay AuthenticationError: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Payment gateway authentication failed: {str(e)}")
    except Exception as e:
        logger.error(f"[CREATE ORDER] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),  # 👈 same here
):
    logger.info(f"[VERIFY PAYMENT] Starting verification for user: {current_user.email}, order_id: {request.razorpay_order_id}")
    logger.info(f"[VERIFY PAYMENT] Payment ID: {request.razorpay_payment_id}, course_id: {request.course_id}")

    try:
        # Generate expected signature
        body = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"
        expected_signature = hmac.new(
            bytes(RAZORPAY_KEY_SECRET, "utf-8"),
            bytes(body, "utf-8"),
            hashlib.sha256,
        ).hexdigest()

        logger.info(f"[VERIFY PAYMENT] Generated signature: {expected_signature[:10]}****")
        logger.info(f"[VERIFY PAYMENT] Provided signature: {request.razorpay_signature[:10]}****")

        if expected_signature != request.razorpay_signature:
            logger.error(f"[VERIFY PAYMENT] Signature mismatch - Expected: {expected_signature}, Provided: {request.razorpay_signature}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature",
            )

        logger.info(f"[VERIFY PAYMENT] Signature verified successfully")

        # ✅ Payment verified, enroll user in course
        if request.course_id not in current_user.enrolled_courses:
            logger.info(f"[VERIFY PAYMENT] Enrolling user in course: {request.course_id}")
            current_user.enrolled_courses.append(request.course_id)
            await current_user.save()
            logger.info(f"[VERIFY PAYMENT] User enrolled successfully")
        else:
            logger.info(f"[VERIFY PAYMENT] User already enrolled in course: {request.course_id}")

        return {"success": True, "message": "Enrolled successfully"}

    except HTTPException as e:
        logger.error(f"[VERIFY PAYMENT] HTTPException: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"[VERIFY PAYMENT] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/user-data")
async def get_user_data(
    current_user: User = Depends(get_current_user),  # 👈 same here
):
    logger.info(f"[USER DATA] Fetching data for user: {current_user.email}")
    try:
        user_data = {
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
        }
        logger.info(f"[USER DATA] Returning: {user_data}")
        return user_data
    except Exception as e:
        logger.error(f"[USER DATA] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
