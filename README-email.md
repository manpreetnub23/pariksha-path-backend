# Email Configuration for Pariksha Path

## Setting up Gmail SMTP for the Application

### 1. Configure Environment Variables

Add these to your `.env` file:

```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
```

### 2. Gmail App Password Setup

For security reasons, Gmail requires an "App Password" instead of your regular password:

1. Go to your Google Account at https://myaccount.google.com/
2. Select "Security" from the left navigation
3. Under "Signing in to Google," select "2-Step Verification" (enable if not already)
4. At the bottom, select "App passwords"
5. Select "Mail" as the app and "Other (Custom name)" as the device
6. Enter "Pariksha Path" and click "Generate"
7. Use the generated 16-character password as your SENDER_PASSWORD

### 3. Features Using Email

The application uses email for:

- Sending welcome messages to new users
- Email verification with OTP
- Login verification with OTP (two-factor authentication)
- Password reset requests
- Notification emails (upcoming feature)

### 4. Troubleshooting

If emails are not being sent:

1. Check console logs for specific errors
2. Verify your App Password is correct
3. Ensure 2-Step Verification is enabled on your Google account
4. Try using a different Gmail account
5. Check if your Gmail account has sending limits/restrictions

### 5. Email Settings

You can control email behavior through these settings:

- `LOGIN_OTP_REQUIRED`: Set to `true` to require OTP verification after login (2FA)
- `SMTP_SERVER` and `SMTP_PORT`: Configure different email providers if needed

Gmail is recommended because:
- Reliable delivery
- Good sending limits (up to 500 emails per day for regular accounts)
- Easy setup with App Passwords
- Free to use
