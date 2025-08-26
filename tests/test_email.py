import asyncio
import sys
import os
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.services.email_service import EmailService
from app.services.otp_service import OTPService


async def test_welcome_email():
    print("\n🧪 Testing Welcome Email...")
    result = await EmailService.send_welcome_email(
        "manavchauhan124@gmail.com", "Test User"
    )
    print("✉️  Welcome Email sent:", "✅ Success" if result else "❌ Failed")


async def test_verification_email():
    print("\n🧪 Testing Verification Email...")
    otp = OTPService.generate_otp()
    print(f"Generated OTP: {otp}")
    result = await EmailService.send_verification_email(
        "manavchauhan124@gmail.com", otp
    )
    print("✉️  Verification Email sent:", "✅ Success" if result else "❌ Failed")


async def test_password_reset_email():
    print("\n🧪 Testing Password Reset Email...")
    otp = OTPService.generate_otp()
    print(f"Generated OTP: {otp}")
    result = await EmailService.send_password_reset_email(
        "manavchauhan124@gmail.com", otp
    )
    print("✉️  Password Reset Email sent:", "✅ Success" if result else "❌ Failed")


async def test_login_otp_email():
    print("\n🧪 Testing Login OTP Email...")
    otp = OTPService.generate_otp()
    print(f"Generated OTP: {otp}")
    result = await EmailService.send_login_otp_email("manavchauhan124@gmail.com", otp)
    print("✉️  Login OTP Email sent:", "✅ Success" if result else "❌ Failed")


async def run_all_tests():
    print("🚀 Starting Email Tests...")
    print(
        "Make sure you've set up your .env file with SENDER_EMAIL and SENDER_PASSWORD"
    )

    try:
        await test_welcome_email()
        await test_verification_email()
        await test_password_reset_email()
        await test_login_otp_email()

        print("\n✨ All tests completed!")

    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        print("\n🔍 Check your .env file contains:")
        print("  SENDER_EMAIL=your-gmail@gmail.com")
        print("  SENDER_PASSWORD=your-16-char-app-password (without spaces)")
        print("  SMTP_SERVER=smtp.gmail.com")
        print("  SMTP_PORT=465")  # Updated to match our new default

        # Additional debugging information
        print("\n📋 Gmail App Password Tips:")
        print("1. Make sure 2-step verification is enabled on your Google account")
        print(
            "2. Generate an App Password from Google Account → Security → App passwords"
        )
        print("3. Copy the 16-character password WITHOUT SPACES")
        print("4. Add to .env file as SENDER_PASSWORD=abcdefghijklmnop")
        print("\n🔒 Gmail Port Information:")
        print("- Port 465: Uses SSL (secure from start)")
        print("- Port 587: Uses STARTTLS (starts insecure, then secures)")
        print("Both should work with our updated code")


if __name__ == "__main__":
    # Replace this email with your test email address
    TEST_EMAIL = "manavchauhan124@gmail.com"

    if "your-test-email" in TEST_EMAIL:
        print("⚠️  Please edit the script to use your actual email address first!")
        sys.exit(1)

    asyncio.run(run_all_tests())
