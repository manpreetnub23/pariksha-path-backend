import re
import html
from typing import Any, Dict, List
import bleach
from bleach.sanitizer import Cleaner


class InputSanitizer:
    """Input sanitization utility to prevent XSS attacks"""

    # Basic XSS patterns to block
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
    ]

    # Allowed HTML tags and attributes for rich text (if needed)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre'
    ]

    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title'],
    }

    def __init__(self):
        """Initialize the HTML cleaner"""
        self.cleaner = Cleaner(
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True,
            strip_comments=True,
        )

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Basic text sanitization - escape HTML and remove XSS patterns"""
        if not isinstance(text, str):
            return ""

        # HTML escape the text first
        escaped = html.escape(text)

        # Remove potential XSS patterns
        for pattern in InputSanitizer.XSS_PATTERNS:
            escaped = re.sub(pattern, '', escaped, flags=re.IGNORECASE | re.DOTALL)

        return escaped.strip()

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """Sanitize HTML content while preserving safe tags"""
        if not isinstance(html_content, str):
            return ""

        # Use bleach for HTML sanitization
        try:
            return bleach.clean(
                html_content,
                tags=InputSanitizer.ALLOWED_TAGS,
                attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
                strip=True,
                strip_comments=True,
            )
        except Exception:
            # Fallback to basic text sanitization if bleach fails
            return InputSanitizer.sanitize_text(html_content)

    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email input"""
        if not isinstance(email, str):
            return ""

        # Basic email validation and sanitization
        email = email.strip().lower()

        # Remove any HTML/XSS content
        email = InputSanitizer.sanitize_text(email)

        # Basic email format check (should match backend validation)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return ""

        return email

    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Sanitize phone number input"""
        if not isinstance(phone, str):
            return ""

        # Remove all non-digit characters except + for international
        phone = re.sub(r'[^\d+]', '', phone)

        # Basic length check (should match backend validation)
        if len(phone) < 10 or len(phone) > 15:
            return ""

        return phone

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize name input"""
        if not isinstance(name, str):
            return ""

        # Remove HTML/XSS content
        name = InputSanitizer.sanitize_text(name)

        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name).strip()

        # Basic length check
        if len(name) < 1 or len(name) > 100:
            return ""

        return name

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL input"""
        if not isinstance(url, str):
            return ""

        # Basic URL sanitization
        url = url.strip()

        # Remove XSS patterns
        url = InputSanitizer.sanitize_text(url)

        # Basic URL format check
        if not url.startswith(('http://', 'https://', 'ftp://')):
            return ""

        return url

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all string values in a dictionary"""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Choose appropriate sanitization based on field name
                if 'email' in key.lower():
                    sanitized[key] = self.sanitize_email(value)
                elif 'phone' in key.lower():
                    sanitized[key] = self.sanitize_phone(value)
                elif 'name' in key.lower() or 'title' in key.lower():
                    sanitized[key] = self.sanitize_name(value)
                elif 'url' in key.lower() or 'link' in key.lower() or 'href' in key.lower():
                    sanitized[key] = self.sanitize_url(value)
                elif 'content' in key.lower() or 'description' in key.lower() or 'message' in key.lower():
                    sanitized[key] = self.sanitize_html(value)
                else:
                    sanitized[key] = self.sanitize_text(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict) else
                    self.sanitize_text(str(item)) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if not isinstance(password, str):
            return False, "Password must be a string"

        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"

        return True, "Password is strong"


# Global sanitizer instance
sanitizer = InputSanitizer()
