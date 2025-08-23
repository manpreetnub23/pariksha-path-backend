import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings


class EmailService:
    @staticmethod
    async def send_verification_email(email: str, otp: str) -> bool:
        """Send verification email with OTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = settings.SENDER_EMAIL
            msg["To"] = email
            msg["Subject"] = "Email Verification - Pariksha Path"

            body = f"""
            Your verification code is: {otp}
            
            This code will expire in 10 minutes.
            If you didn't request this, please ignore this email.
            """

            msg.attach(MIMEText(body, "plain"))

            # Send email
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
