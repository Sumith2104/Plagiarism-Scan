import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_welcome_email(to_email: str, full_name: str = None):
    """
    Send a welcome email to the user asynchronously using SMTP.
    Requires EMAIL_ADDRESS and EMAIL_PASSWORD in .env.
    """
    sender_email = settings.EMAIL_ADDRESS
    sender_password = settings.EMAIL_PASSWORD

    if not sender_email or not sender_password:
        logger.warning("Email credentials not configured. Skipping welcome email.")
        return

    name_str = full_name if full_name else "User"

    subject = "Welcome to PlagiaScan!"
    body = f"""
    <html>
    <body>
        <h2>Welcome to PlagiaScan, {name_str}!</h2>
        <p>Thank you for registering an account with us. Your account has been successfully created.</p>
        <p>You can now upload documents and perform plagiarism scans using our advanced ML detection engine.</p>
        <br>
        <p>Best regards,</p>
        <p>The PlagiaScan Team</p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"PlagiaScan <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Welcome email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {to_email}: {e}")
