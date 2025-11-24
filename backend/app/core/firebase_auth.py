import firebase_admin
from firebase_admin import auth, credentials
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
# Expects GOOGLE_APPLICATION_CREDENTIALS env var to point to service account JSON
# OR explicit path passed to credentials.Certificate()
try:
    if not firebase_admin._apps:
        # Check if we have the JSON content in an env var (for Render/Cloud)
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            import json
            cred = credentials.Certificate(json.loads(service_account_json))
        else:
            # Fallback to file path
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "firebase-credentials.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                logger.warning("Firebase credentials not found. Google Sign-In will fail.")
                cred = None
        
        if cred:
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin: {e}")

def verify_google_token(token: str):
    """
    Verifies a Firebase ID token.
    Returns the decoded token dict if valid, else None.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None
