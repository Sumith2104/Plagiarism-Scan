from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
def startup_event():
    import subprocess
    from app.db.session import engine
    from app.models import Base
    
    try:
        print("DEBUG: Starting database setup...")
        
        # 1. Try Alembic Migrations first (Best Practice)
        try:
            print("DEBUG: Running alembic migrations...")
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            print("Database migrations completed successfully.")
        except Exception as e:
            print(f"Alembic migration failed: {e}")
            print("DEBUG: Falling back to direct table creation...")
            
            # 2. Failsafe: Create tables directly if Alembic failed
            Base.metadata.create_all(bind=engine)
            print("DEBUG: Direct table creation completed.")
            
    except Exception as e:
        print(f"Critical Database Setup Failed: {e}")
        # We don't raise here to allow app to start even if migration fails (e.g. local dev)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://plagiascan.vercel.app",
        "https://plagiarism-scan.vercel.app", # Just in case
        "*" # Allow all for now to debug
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.endpoints import documents, scans, auth

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(documents.router, prefix=f"{settings.API_V1_STR}/documents", tags=["documents"])
app.include_router(scans.router, prefix=f"{settings.API_V1_STR}/scans", tags=["scans"])

@app.get("/")
def root():
    return {"message": "Welcome to PlagiaScan API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
