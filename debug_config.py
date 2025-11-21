import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.core.config import settings
    print("Config loaded successfully")
    print(f"DB URL: {settings.DATABASE_URL}")
except Exception as e:
    print(f"Error loading config: {e}")
    import traceback
    traceback.print_exc()
