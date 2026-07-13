import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL (Default to local dev if not set)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://plagiascan:plagiascan_dev@localhost:5432/plagiascan")

def view_users():
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        print("\n=== Registered Users ===")
        result = db.execute(text("SELECT id, email, full_name, role FROM users"))
        users = result.fetchall()
        
        if not users:
            print("No users found.")
        else:
            print(f"{'ID':<5} | {'Email':<30} | {'Full Name':<20} | {'Role'}")
            print("-" * 70)
            for user in users:
                print(f"{user.id:<5} | {user.email:<30} | {user.full_name or 'N/A':<20} | {user.role}")
        print("========================\n")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Make sure the database container is running (docker-compose up -d db).")

if __name__ == "__main__":
    view_users()
