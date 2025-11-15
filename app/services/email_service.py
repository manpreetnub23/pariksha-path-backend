import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, body: str) -> bool:
        """Send email using Hostinger SMTP with SSL first, fallback to TLS"""
        try:
            if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD:
                print("⚠ SMTP not configured — printing email instead\n")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Body:\n{body}\n")
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SENDER_EMAIL
            msg["To"] = to_email
            msg.attach(MIMEText(body, "html"))

            # Try SSL first (recommended for Hostinger)
            try:
                with smtplib.SMTP_SSL(settings.SMTP_SERVER, 465, timeout=10) as server:
                    server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
                    server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())

                print(f"✔ Email sent (SSL/465) → {to_email}")
                return True

            except Exception:
                print("⚠ SSL failed — retrying with TLS (587)")

                with smtplib.SMTP(settings.SMTP_SERVER, 587, timeout=10) as server:
                    server.starttls()
                    server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
                    server.sendmail(settings.SENDER_EMAIL, to_email, msg.as_string())

                print(f"✔ Email sent (TLS/587) → {to_email}")
                return True

        except Exception as e:
            print(f"❌ Email send failed: {e}")
            logger.error(f"Email error: {e}")
            return False

    # -----------------------------------------------------------
    # HTML TEMPLATE (Universal Green + Yellow Theme)
    # -----------------------------------------------------------
    @staticmethod
    def otp_template(title: str, description: str, otp: str, color: str):
        """Generate a short, themed OTP email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8" />
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #E8F5E9;
                    padding: 20px;
                }}
                .card {{
                    max-width: 500px;
                    margin: auto;
                    background: #fff;
                    border-radius: 12px;
                    padding: 30px;
                    border-left: 8px solid {color};
                }}
                .title {{
                    font-size: 22px;
                    font-weight: bold;
                    color: {color};
                    margin-bottom: 10px;
                }}
                .text {{
                    color: #555;
                    font-size: 15px;
                    line-height: 1.5;
                }}
                .otp-box {{
                    margin: 25px 0;
                    background: {color};
                    color: #fff;
                    padding: 18px;
                    text-align: center;
                    font-size: 32px;
                    letter-spacing: 6px;
                    border-radius: 8px;
                    font-weight: bold;
                }}
                .footer {{
                    margin-top: 25px;
                    font-size: 13px;
                    color: #777;
                    text-align: center;
                }}
                a {{
                    color: {color};
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="title">{title}</div>
                <p class="text">{description}</p>
                <div class="otp-box">{otp}</div>
                <p class="text">This code is valid for <b>10 minutes</b>.</p>
                <div class="footer">
                    Need help?  
                    <a href="mailto:support@myparikshapath.in">support@myparikshapath.in</a><br>
                    © 2025 My Parikshapath
                </div>
            </div>
        </body>
        </html>
        """

    # -----------------------------------------------------------
    # OTP EMAIL TYPES
    # -----------------------------------------------------------

    @staticmethod
    async def send_verification_email(email: str, otp: str) -> bool:
        subject = "Verify Your Email - My Parikshapath"
        body = EmailService.otp_template(
            title="Verify Your Email",
            description="Use the verification code below to complete your registration on My Parikshapath.",
            otp=otp,
            color="#2E7D32"  # Green
        )
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_password_reset_email(email: str, otp: str) -> bool:
        subject = "Password Reset Code - My Parikshapath"
        body = EmailService.otp_template(
            title="Reset Your Password",
            description="Use the code below to reset your password on My Parikshapath.",
            otp=otp,
            color="#FBC02D"  # Yellow
        )
        return await EmailService.send_email(email, subject, body)

    @staticmethod
    async def send_login_otp_email(email: str, otp: str) -> bool:
        subject = "Login Verification Code - My Parikshapath"
        body = EmailService.otp_template(
            title="Login Verification",
            description="Enter the verification code below to complete your login.",
            otp=otp,
            color="#2E7D32"  # Green
        )
        return await EmailService.send_email(email, subject, body)
