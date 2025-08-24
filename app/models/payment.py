from beanie import Document
from pydantic import Field, BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentGateway(str, Enum):
    RAZORPAY = "razorpay"
    PAYU = "payu"
    UPI = "upi"


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class PaymentReceipt(BaseModel):
    """Receipt information"""

    receipt_number: str
    receipt_url: Optional[str] = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_sent_to_email: bool = False
    sent_at: Optional[datetime] = None


class PaymentPurpose(str, Enum):
    COURSE = "course"
    TEST_SERIES = "test_series"
    STUDY_MATERIAL = "study_material"
    BUNDLE = "bundle"  # Combined products


class Coupon(Document):
    """Discount coupon model"""

    code: str  # Coupon code
    description: str
    discount_type: DiscountType
    discount_value: float  # Percentage or fixed amount

    # Validity
    valid_from: datetime
    valid_until: datetime
    is_active: bool = True

    # Usage limits
    max_uses: Optional[int] = None
    current_uses: int = 0
    max_uses_per_user: Optional[int] = None

    # Applicability
    min_cart_value: Optional[float] = None
    applicable_courses: List[str] = []  # Empty means all courses
    applicable_test_series: List[str] = []  # Empty means all test series
    applicable_materials: List[str] = []  # Empty means all materials

    # Tracking
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "coupons"


class Payment(Document):
    user_id: str
    amount: float
    purpose: PaymentPurpose

    # Payment details
    payment_id: str  # Gateway payment ID
    order_id: Optional[str] = None
    gateway: PaymentGateway
    status: PaymentStatus

    # Item details
    items: List[Dict[str, Any]] = (
        []
    )  # [{"id": "id", "type": "course", "name": "name", "amount": 100}]
    coupon_code: Optional[str] = None
    coupon_discount: float = 0
    original_amount: float  # Pre-discount amount

    # Transaction details
    transaction_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    gateway_response: Dict[str, Any] = {}
    failure_reason: Optional[str] = None
    retry_count: int = 0

    # Receipt
    receipt: Optional[PaymentReceipt] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "payments"

    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)
