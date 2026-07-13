from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.on_event("startup")
def startup_event():
    from app.core.config import settings

    if settings.use_fluxbase:
        # --- Fluxbase Mode ---
        try:
            print("DEBUG: Initializing Fluxbase tables...")
            from app.db.fluxbase import initialize_fluxbase_tables, get_fluxbase_client
            client = get_fluxbase_client()
            if client.health_check():
                initialize_fluxbase_tables()
                print("DEBUG: Fluxbase ready - OK")
            else:
                print("WARNING: Fluxbase health check failed. Check your API key / project ID.")
        except Exception as e:
            print(f"Fluxbase setup failed: {e}")
    else:
        # --- SQLite Fallback Mode ---
        try:
            print("DEBUG: Fluxbase credentials not set. Using SQLite fallback...")
            from app.db.session import engine
            from app.models import Base
            Base.metadata.create_all(bind=engine, checkfirst=True)
            print("DEBUG: SQLite tables ready - OK")
        except Exception as e:
            print(f"Critical Database Setup Failed: {e}")



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

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Serve React Frontend SPA ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
import os

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "../../frontend/dist"))

# Custom 404 Exception Handler for React Router SPA Fallback
from fastapi.exception_handlers import http_exception_handler

@app.exception_handler(404)
async def spa_404_handler(request, exc):
    # Return standard JSON 404 for API/docs requests
    if request.url.path.startswith("/api/") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
        return await http_exception_handler(request, exc)
        
    index_file = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return await http_exception_handler(request, exc)

# Mount the static files directory at the root last
if os.path.exists(FRONTEND_DIST_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")
