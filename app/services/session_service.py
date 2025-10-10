from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from ..models.user_session import UserSession
from ..db import init_beanie_if_needed


class SessionService:
    """Service for managing user sessions and refresh token blacklisting"""

    @staticmethod
    def extract_device_info(user_agent: str = None, ip_address: str = None) -> Dict[str, Any]:
        """Extract device information from request headers"""
        device_info = {}

        if user_agent:
            # Basic browser detection
            user_agent_lower = user_agent.lower()
            if 'mobile' in user_agent_lower or 'android' in user_agent_lower or 'iphone' in user_agent_lower:
                device_info['type'] = 'mobile'
            elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
                device_info['type'] = 'tablet'
            else:
                device_info['type'] = 'desktop'

            # Browser detection
            if 'chrome' in user_agent_lower:
                device_info['browser'] = 'Chrome'
            elif 'firefox' in user_agent_lower:
                device_info['browser'] = 'Firefox'
            elif 'safari' in user_agent_lower:
                device_info['browser'] = 'Safari'
            elif 'edge' in user_agent_lower:
                device_info['browser'] = 'Edge'
            else:
                device_info['browser'] = 'Unknown'

        if ip_address:
            device_info['ip_address'] = ip_address

        return device_info

    @staticmethod
    async def create_session(
        user_id: str,
        refresh_token: str,
        user_agent: str = None,
        ip_address: str = None
    ) -> UserSession:
        """Create a new user session"""
        await init_beanie_if_needed()

        device_info = SessionService.extract_device_info(user_agent, ip_address)

        session = UserSession.create_from_refresh_token(
            user_id=user_id,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Set expiry to 7 days from now (same as refresh token)
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        await session.insert()
        session.add_activity_log("session_created", "New session created")

        return session

    @staticmethod
    async def validate_session(refresh_token: str) -> Optional[UserSession]:
        """Validate if a refresh token corresponds to an active session"""
        await init_beanie_if_needed()

        session = await UserSession.find_active_session_by_refresh_token(refresh_token)

        if session:
            # Update activity timestamp
            session.update_activity()
            await session.save()

        return session

    @staticmethod
    async def blacklist_refresh_token(refresh_token: str) -> bool:
        """Blacklist a refresh token by deactivating its session"""
        await init_beanie_if_needed()

        success = await UserSession.blacklist_refresh_token(refresh_token)

        if success:
            print(f"🔒 Refresh token blacklisted successfully")

        return success

    @staticmethod
    async def invalidate_all_user_sessions(user_id: str) -> int:
        """Invalidate all active sessions for a user (force logout everywhere)"""
        await init_beanie_if_needed()

        invalidated_count = await UserSession.invalidate_all_user_sessions(user_id)

        if invalidated_count > 0:
            print(f"🚪 Invalidated {invalidated_count} sessions for user {user_id}")

        return invalidated_count

    @staticmethod
    async def get_user_sessions(user_id: str, active_only: bool = True) -> List[UserSession]:
        """Get all sessions for a user"""
        await init_beanie_if_needed()

        if active_only:
            return await UserSession.get_user_active_sessions(user_id)
        else:
            return await UserSession.find({"user_id": user_id}).sort([("last_activity", -1)]).to_list()

    @staticmethod
    async def cleanup_expired_sessions() -> int:
        """Clean up expired sessions (should be run periodically)"""
        await init_beanie_if_needed()

        cleaned_count = await UserSession.cleanup_expired_sessions()

        if cleaned_count > 0:
            print(f"🧹 Cleaned up {cleaned_count} expired sessions")

        return cleaned_count

    @staticmethod
    async def get_session_stats(user_id: str) -> Dict[str, Any]:
        """Get session statistics for a user"""
        await init_beanie_if_needed()

        all_sessions = await SessionService.get_user_sessions(user_id, active_only=False)
        active_sessions = await SessionService.get_user_sessions(user_id, active_only=True)

        # Group sessions by device type
        device_types = {}
        for session in all_sessions:
            device_type = session.device_info.get('type', 'unknown')
            device_types[device_type] = device_types.get(device_type, 0) + 1

        return {
            "total_sessions": len(all_sessions),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(all_sessions) - len(active_sessions),
            "device_breakdown": device_types,
            "oldest_session": min((s.created_at for s in all_sessions), default=None),
            "newest_session": max((s.created_at for s in all_sessions), default=None)
        }

    @staticmethod
    async def check_concurrent_sessions(user_id: str, max_sessions: int = 5) -> Dict[str, Any]:
        """Check if user has exceeded concurrent session limit"""
        await init_beanie_if_needed()

        active_sessions = await SessionService.get_user_sessions(user_id, active_only=True)

        return {
            "current_sessions": len(active_sessions),
            "max_allowed": max_sessions,
            "exceeded": len(active_sessions) >= max_sessions,
            "sessions": [session.to_dict() for session in active_sessions]
        }

    @staticmethod
    async def enforce_session_limit(user_id: str, max_sessions: int = 5) -> List[str]:
        """Enforce session limit by removing oldest sessions"""
        await init_beanie_if_needed()

        active_sessions = await SessionService.get_user_sessions(user_id, active_only=True)

        if len(active_sessions) < max_sessions:
            return []

        # Sort by last activity (oldest first)
        sessions_to_remove = sorted(active_sessions, key=lambda s: s.last_activity)[:-max_sessions + 1]

        removed_session_ids = []
        for session in sessions_to_remove:
            session.deactivate()
            await session.save()
            removed_session_ids.append(str(session.id))

        if removed_session_ids:
            print(f"🔧 Enforced session limit for user {user_id}, removed {len(removed_session_ids)} sessions")

        return removed_session_ids
