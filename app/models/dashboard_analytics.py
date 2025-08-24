from datetime import datetime, timezone, date
from typing import Dict, List, Any, Optional
from beanie import Document
from pydantic import Field, BaseModel
from enum import Enum


class TimeRange(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class AdminDashboardMetrics(Document):
    """Aggregated metrics for admin dashboard"""

    # Users
    total_users: int = 0
    active_users: int = 0  # Active in last 30 days
    new_users_today: int = 0
    new_users_this_week: int = 0
    new_users_this_month: int = 0

    # Revenue
    revenue_today: float = 0
    revenue_this_week: float = 0
    revenue_this_month: float = 0
    revenue_by_course: Dict[str, float] = {}
    revenue_by_test_series: Dict[str, float] = {}

    # Test activity
    tests_taken_today: int = 0
    tests_taken_this_week: int = 0
    tests_taken_this_month: int = 0
    popular_tests: List[Dict[str, Any]] = []  # [{id, name, attempt_count}]

    # Course engagement
    popular_courses: List[Dict[str, Any]] = []
    course_completion_rates: Dict[str, float] = {}

    # Material usage
    popular_materials: List[Dict[str, Any]] = []
    material_downloads_today: int = 0

    # User demographics
    users_by_exam_category: Dict[str, int] = {}
    users_by_region: Dict[str, int] = {}

    # Time series data (last 30 days)
    daily_signups: List[Dict[str, Any]] = []  # [{date, count}]
    daily_revenue: List[Dict[str, Any]] = []
    daily_test_attempts: List[Dict[str, Any]] = []

    # Update tracking
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "admin_dashboard_metrics"


class ExamCategoryAnalytics(Document):
    """Analytics specific to each exam category"""

    category: str  # e.g., "medical", "engineering"
    sub_category: Optional[str] = None  # e.g., "NEET", "JEE Main"

    # Key metrics
    total_enrolled_users: int = 0
    active_users_30d: int = 0
    avg_test_score: float = 0

    # Content performance
    top_courses: List[Dict[str, Any]] = []
    top_tests: List[Dict[str, Any]] = []
    top_materials: List[Dict[str, Any]] = []

    # Question analytics
    easiest_topics: List[Dict[str, Any]] = []
    hardest_topics: List[Dict[str, Any]] = []

    # Performance distribution
    score_distribution: Dict[str, int] = {}  # {"0-10%": 5, "10-20%": 10, ...}

    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "exam_category_analytics"


class RevenueAnalytics(Document):
    """Detailed revenue tracking and analysis"""

    # Daily revenue tracking
    date: date
    total_revenue: float = 0
    course_revenue: float = 0
    test_series_revenue: float = 0
    refunds: float = 0
    net_revenue: float = 0

    # Payment method breakdown
    payment_method_breakdown: Dict[str, float] = {}  # {"razorpay": 500, "payu": 300}

    # Product breakdown
    top_selling_items: List[Dict[str, Any]] = []
    revenue_by_category: Dict[str, float] = {}

    # User metrics
    new_paying_users: int = 0
    repeat_customers: int = 0
    avg_order_value: float = 0

    class Settings:
        name = "revenue_analytics"
        indexes = [
            "date",  # For fast date-based lookups
        ]
