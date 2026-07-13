from app.db.session import engine, Base
from app.models import user, document, scan

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
