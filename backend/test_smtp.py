"""
SMTP Authentication Diagnostics & Testing Utility
Run this script to verify your Gmail SMTP credentials configured in .env:
    python test_smtp.py
"""
import sys
from app.core.config import settings
from app.core.email import get_smtp_connection, send_welcome_email

def test_smtp():
    print("=" * 60)
    print(" PlagiaScan SMTP Authentication Diagnostics")
    print("=" * 60)
    print(f"SMTP Server   : {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
    print(f"SSL Enabled   : {settings.SMTP_USE_SSL}")
    print(f"Sender Email  : {settings.EMAIL_ADDRESS or '[NOT CONFIGURED]'}")
    
    pwd_masked = '*' * len(settings.EMAIL_PASSWORD) if settings.EMAIL_PASSWORD else '[NOT CONFIGURED]'
    print(f"Password/Key  : {pwd_masked}")
    print("-" * 60)

    if not settings.EMAIL_ADDRESS or not settings.EMAIL_PASSWORD:
        print("[!] Error: EMAIL_ADDRESS or EMAIL_PASSWORD missing in backend/.env")
        print("\nPlease add the following to your backend/.env:")
        print("EMAIL_ADDRESS=your_email@gmail.com")
        print("EMAIL_PASSWORD=your_16_character_app_password")
        return

    print("Connecting to SMTP server and verifying authentication credentials...")
    try:
        server = get_smtp_connection()
        print("[OK] SMTP Connection & Authentication SUCCESSFUL!")
        server.quit()

        target_email = settings.EMAIL_ADDRESS
        print(f"\nSending a test branded welcome email to: {target_email} ...")
        success = send_welcome_email(target_email, "Integrity Administrator")
        if success:
            print(f"[OK] Test email sent successfully to {target_email}!")
            print("Check your Gmail inbox (and Spam folder) to verify formatting.")
        else:
            print("[!] Could not dispatch test email. Check server logs.")

    except Exception as e:
        print(f"\n[FAIL] SMTP Authentication Failed!")
        print(f"Error Details: {e}\n")
        print("Troubleshooting steps for Gmail:")
        print("1. Ensure 2-Step Verification is active on your Google Account.")
        print("2. Generate a dedicated App Password at: https://myaccount.google.com/apppasswords")
        print("   (Select 'Mail' or 'Other' and name it 'PlagiaScan')")
        print("3. Copy the 16-character code (e.g. 'abcd efgh ijkl mnop') into backend/.env:")
        print("   EMAIL_PASSWORD=abcdefghijklmnop")

if __name__ == "__main__":
    test_smtp()
