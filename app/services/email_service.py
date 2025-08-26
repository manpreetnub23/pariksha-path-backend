import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings


class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str) -> bool:
        """Send email using SMTP"""
        try:
            # Check if credentials are available
            if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD:
                print("Warning: Email credentials not configured")
                # Fall back to console output for development/testing
                print(f"\n--- Email to: {to_email} ---")
                print(f"Subject: {subject}")
                print(f"Content: {body}")
                print("--- End of email ---\n")
                return True  # Return true in development to allow flow to continue

            # Create message
            msg = MIMEMultipart()
            msg["From"] = settings.SENDER_EMAIL
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Send email based on port
            # Port 465 uses SSL, Port 587 uses STARTTLS
            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_SERVER, settings.SMTP_PORT)
            else:
                server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
                server.starttls()  # Enable secure connection

            # Remove any spaces from password (Gmail app passwords sometimes have spaces)
            password = settings.SENDER_PASSWORD.replace(" ", "")

            server.login(settings.SENDER_EMAIL, password)
            server.send_message(msg)
            server.quit()

            print(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
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
Pariksha Path Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_password_reset_email(email: str, otp: str) -> bool:
        """Send password reset email with OTP"""
        subject = "Password Reset - Pariksha Path"
        body = f"""
Dear User,

You requested a password reset for your Pariksha Path account.

Your password reset code is: {otp}

This code will expire in 10 minutes.
If you didn't request this, please ignore this email.

Best regards,
Pariksha Path Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_login_otp_email(email: str, otp: str) -> bool:
        """Send login verification OTP"""
        subject = "Login Verification - Pariksha Path"
        body = f"""
Dear User,

To complete your login to Pariksha Path, please use the following verification code:

Your login verification code is: {otp}

This code will expire in 10 minutes.
If you didn't attempt to login, please contact our support team immediately.

Best regards,
Pariksha Path Team
        """
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_welcome_email(email: str, name: str) -> bool:
        """Send welcome email to new users"""
        subject = "Welcome to Pariksha Path!"
        body = f"""
Dear {name},

Welcome to Pariksha Path! We're excited to have you join our community.

Your account has been created successfully. To get started:

1. Complete your profile
2. Browse available courses and materials
3. Explore our mock tests and practice resources

If you have any questions, please don't hesitate to contact our support team.

Best regards,
Pariksha Path Team
        """
        return await EmailService.send_email(email, subject, body)
