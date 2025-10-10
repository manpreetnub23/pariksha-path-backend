from beanie import Document
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import json


class UserSession(Document):
    """
    Model for tracking active user sessions with refresh token blacklisting
    """

    user_id: str = Field(..., description="User ID this session belongs to")
    refresh_token_hash: str = Field(
        ..., description="SHA-256 hash of refresh token for blacklisting"
    )
    device_info: Dict[str, Any] = Field(
        default_factory=dict, description="Device/browser information"
    )
    ip_address: Optional[str] = Field(None, description="IP address of the session")
    user_agent: Optional[str] = Field(None, description="User agent string")
    location: Optional[Dict[str, Any]] = Field(
        None, description="Geolocation data if available"
    )

    # Session metadata
    is_active: bool = Field(default=True, description="Whether this session is active")
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last activity timestamp",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Session creation timestamp",
    )
    expires_at: Optional[datetime] = Field(None, description="Session expiry timestamp")

    # Security tracking
    suspicious_activity: bool = Field(
        default=False, description="Flag for suspicious activity"
    )
    activity_log: list[Dict[str, Any]] = Field(
        default_factory=list, description="Recent activity log"
    )

    class Settings:
        name = "user_sessions"

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)
        self.add_activity_log("activity_update", "Session activity updated")

    def add_activity_log(
        self, action: str, description: str, metadata: Dict[str, Any] = None
    ):
        """Add entry to activity log"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "description": description,
            "metadata": metadata or {},
        }

        # Keep only last 10 activities
        self.activity_log.append(log_entry)
        if len(self.activity_log) > 10:
            self.activity_log = self.activity_log[-10:]

    def mark_suspicious(self, reason: str, metadata: Dict[str, Any] = None):
        """Mark session as suspicious"""
        self.suspicious_activity = True
        self.add_activity_log("suspicious_activity", reason, metadata)

    def deactivate(self):
        """Deactivate the session"""
        self.is_active = False
        self.add_activity_log("session_deactivated", "Session manually deactivated")

    @classmethod
    def hash_refresh_token(cls, refresh_token: str) -> str:
        """Create SHA-256 hash of refresh token for blacklisting"""
        return hashlib.sha256(refresh_token.encode()).hexdigest()

    @classmethod
    def create_from_refresh_token(
        cls,
        user_id: str,
        refresh_token: str,
        device_info: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None,
    ) -> "UserSession":
        """Create new session from refresh token"""
        return cls(
            user_id=user_id,
            refresh_token_hash=cls.hash_refresh_token(refresh_token),
            device_info=device_info or {},
            ip_address=ip_address,
            user_agent=user_agent,
            last_activity=datetime.now(timezone.utc),
        )

    @classmethod
    async def find_active_session_by_refresh_token(
        cls, refresh_token: str
    ) -> Optional["UserSession"]:
        """Find active session by refresh token hash"""
        token_hash = cls.hash_refresh_token(refresh_token)
        return await cls.find_one({"refresh_token_hash": token_hash, "is_active": True})

    @classmethod
    async def blacklist_refresh_token(cls, refresh_token: str) -> bool:
        """Blacklist a refresh token by marking its session as inactive"""
        session = await cls.find_active_session_by_refresh_token(refresh_token)
        if session:
            session.deactivate()
            await session.save()
            return True
        return False

    @classmethod
    async def get_user_active_sessions(cls, user_id: str) -> list["UserSession"]:
        """Get all active sessions for a user"""
        return (
            await cls.find({"user_id": user_id, "is_active": True})
            .sort([("last_activity", -1)])
            .to_list()
        )

    @classmethod
    async def invalidate_all_user_sessions(cls, user_id: str) -> int:
        """Invalidate all active sessions for a user"""
        sessions = await cls.get_user_active_sessions(user_id)
        for session in sessions:
            session.deactivate()
            await session.save()
        return len(sessions)

    @classmethod
    async def cleanup_expired_sessions(cls) -> int:
        """Clean up expired sessions (for background task)"""
        expired_sessions = await cls.find(
            {"expires_at": {"$lt": datetime.now(timezone.utc)}, "is_active": True}
        ).to_list()

        for session in expired_sessions:
            session.deactivate()
            await session.save()

        return len(expired_sessions)

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for API responses"""
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "device_info": self.device_info,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "location": self.location,
            "is_active": self.is_active,
            "last_activity": self.last_activity,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "suspicious_activity": self.suspicious_activity,
            "activity_count": len(self.activity_log),
        }
