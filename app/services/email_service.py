import resend
from ..config import settings


class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str) -> bool:
        """Send email using Resend SDK"""
        try:
            # Check if API key is available
            if not settings.SENDER_PASSWORD:
                print("Warning: Resend API key not configured")
                # Fall back to console output for development/testing
                print(f"\n--- Email to: {to_email} ---")
                print(f"Subject: {subject}")
                print(f"Content: {body}")
                print("--- End of email ---\n")
                return True  # Return true in development to allow flow to continue

            # Set API key (do this once per request)
            resend.api_key = settings.SENDER_PASSWORD

            # Prepare email parameters
            params = {
                "from": settings.SENDER_EMAIL
                or "My Parikshpath <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": body,  # Use HTML for better formatting
            }

            # Send email using Resend SDK
            result = resend.Emails.send(params)

            if result and result.get("id"):
                print(
                    f"Email sent successfully to {to_email} via Resend (ID: {result['id']})"
                )
                return True
            else:
                print(f"Failed to send email - no ID returned: {result}")
                return False

        except Exception as e:
            if "API key is invalid" in str(e):
                print(f"Resend API key is invalid: {e}")
                print("Please check your Resend API key in the .env file")
            else:
                print(f"Resend API error: {e}")
            # Fall back to console output for development
            print(f"\n--- Email to: {to_email} ---")
            print(f"Subject: {subject}")
            print(f"Content: {body}")
            print("--- End of email ---\n")
            return False

    @staticmethod
    async def send_verification_email(email: str, otp: str) -> bool:
        """Send verification email with OTP"""
        subject = "Email Verification - Pariksha Path"
        body = f"""
Dear User,

Your verification code is: {otp}

This code will expire in 10 minutes.
If you didn't request this, please ignore this email.

Best regards,
My Parikshapath Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_password_reset_email(email: str, otp: str) -> bool:
        """Send password reset email with OTP"""
        subject = "Password Reset - Pariksha Path"
        body = f"""
Dear User,

You requested a password reset for your My Parikshapath account.

Your password reset code is: {otp}

This code will expire in 10 minutes.
If you didn't request this, please ignore this email.

Best regards,
My Parikshapath Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_login_otp_email(email: str, otp: str) -> bool:
        """Send login verification OTP"""
        subject = "Login Verification - My Parikshapath"
        body = f"""
Dear User,

To complete your login to Pariksha Path, please use the following verification code:

Your login verification code is: {otp}

This code will expire in 10 minutes.
If you didn't attempt to login, please contact our support team immediately.

Best regards,
My Parikshapath Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_welcome_email(email: str, name: str) -> bool:
        """Send welcome email to new users"""
        subject = "Welcome to My Parikshapath!"
        body = f"""
Dear {name},

Welcome to My Parikshapath! We're excited to have you join our community.

Your account has been created successfully. To get started:

1. Complete your profile
2. Browse available courses and materials
3. Explore our mock tests and practice resources

If you have any questions, please don't hesitate to contact our support team.

Best regards,
My Parikshapath Team
        """
        return await EmailService.send_email(email, subject, body)
