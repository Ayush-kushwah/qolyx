import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.core.config import settings

logger = logging.getLogger("qolyx.users.email")

def send_verification_email(to_email: str, code: str) -> bool:
    """Send 6-digit OTP verification email to user."""
    try:
        # Check if SMTP is configured
        if not settings.SMTP_HOST or not settings.SMTP_USER:
            # If no SMTP, log and skip (self-hosted/dev mode)
            logger.info(f"SMTP not configured. Auto-logged verification code for {to_email}: {code}")
            return True
        
        # Build email
        subject = "Qolyx — Email Verification Code"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: #f7fafc;
                    margin: 0;
                    padding: 20px;
                    color: #2d3748;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 32px 24px;
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
                    border: 1px solid #e2e8f0;
                }}
                .header {{
                    text-align: center;
                    padding-bottom: 24px;
                    border-bottom: 2px solid #edf2f7;
                }}
                .code {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #10B981;
                    letter-spacing: 4px;
                    text-align: center;
                    background-color: #f8fafc;
                    padding: 16px;
                    border-radius: 8px;
                    border: 1px solid #edf2f7;
                    margin: 24px 0;
                }}
                .footer {{
                    text-align: center;
                    padding-top: 24px;
                    border-top: 1px solid #edf2f7;
                    color: #a0aec0;
                    font-size: 11px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="color: #10B981; margin: 0;">◆ Qolyx</h1>
                    <p style="margin: 4px 0 0 0; color: #718096; font-size: 14px;">Data Reliability Platform</p>
                </div>
                <h2 style="font-size: 18px; margin-top: 24px; color: #1a202c;">Verify Your Email Address</h2>
                <p style="font-size: 14px; line-height: 1.6; color: #4a5568;">
                    Thank you for registering an operator account. Please use the 6-digit verification code below to activate your account:
                </p>
                <div class="code">{code}</div>
                <p style="font-size: 13px; line-height: 1.6; color: #718096;">
                    This code will expire in 24 hours. If you did not request this registration, you can safely ignore this email.
                </p>
                <div class="footer">
                    <p>© 2026 Qolyx. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_body = f"""
        Qolyx — Email Verification
        
        Your verification code is: {code}
        
        This code will expire in 24 hours.
        """
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.ALERT_EMAIL_FROM or settings.ALERT_EMAIL_SENDER or "alerts@qolyx.io"
        msg["To"] = to_email
        
        part1 = MIMEText(plain_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)
        
        smtp_server = settings.SMTP_HOST
        smtp_port = int(settings.SMTP_PORT or 587)
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10.0)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10.0)
            if smtp_port == 587 or smtp_server == "smtp.gmail.com":
                server.ehlo()
                server.starttls()
                server.ehlo()
                
        with server:
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(msg["From"], [to_email], msg.as_string())
            
        logger.info(f"Verification email successfully sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}", exc_info=True)
        return False
