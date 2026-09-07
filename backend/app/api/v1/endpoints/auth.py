from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core import auth
from app.models.user import User
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/login", response_model=dict)
async def login_access_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Accepts form-data (OAuth2 / URL-encoded), JSON body, or query parameters.
    Performs case-insensitive email matching.
    """
    email_or_user = None
    password = None

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            body = await request.json()
            email_or_user = body.get("username") or body.get("email")
            password = body.get("password")
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            email_or_user = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    # Fallback to query params if still empty
    if not email_or_user:
        email_or_user = request.query_params.get("username") or request.query_params.get("email")
    if not password:
        password = request.query_params.get("password")

    if not email_or_user or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email/username and password are required"
        )

    cleaned_email = str(email_or_user).lower().strip()
    user = db.query(User).filter(func.lower(User.email) == cleaned_email).first()
    if not user or not auth.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": getattr(user.role, "value", str(user.role or "user"))
        }
    }

@router.post("/register", response_model=dict)
async def register_user(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email: Optional[str] = None,
    password: Optional[str] = None,
    full_name: Optional[str] = None,
):
    """
    Accepts JSON body, form-data, or URL query parameters.
    Performs case-insensitive validation and normalizes emails.
    """
    req_email = email
    req_password = password
    req_full_name = full_name

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            body = await request.json()
            req_email = body.get("email") or req_email
            req_password = body.get("password") or req_password
            req_full_name = body.get("full_name") or req_full_name
        except Exception:
            pass
    elif "form" in content_type:
        try:
            form = await request.form()
            req_email = form.get("email") or req_email
            req_password = form.get("password") or req_password
            req_full_name = form.get("full_name") or req_full_name
        except Exception:
            pass

    if not req_email or not req_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    cleaned_email = str(req_email).lower().strip()
    if "@" not in cleaned_email or "." not in cleaned_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address"
        )

    user = db.query(User).filter(func.lower(User.email) == cleaned_email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered. Please sign in instead."
        )

    new_user = User(
        email=cleaned_email,
        password_hash=auth.get_password_hash(req_password),
        full_name=req_full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send welcome email asynchronously if configured
    try:
        from app.core.email import send_welcome_email
        background_tasks.add_task(send_welcome_email, new_user.email, new_user.full_name)
    except Exception:
        pass

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        subject=new_user.id, expires_delta=access_token_expires
    )
    return {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "access_token": access_token,
        "token_type": "bearer",
        "message": "User registered successfully"
    }

@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_user)):
    created_at_val = current_user.created_at
    if hasattr(created_at_val, "isoformat"):
        created_at_str = created_at_val.isoformat()
    else:
        created_at_str = str(created_at_val) if created_at_val else None

    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role or "user")

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name or current_user.email.split("@")[0],
        "role": role_val,
        "created_at": created_at_str,
    }

@router.post("/login/google", response_model=dict)
def login_google(
    token_data: dict,
    db: Session = Depends(get_db)
):
    from app.core.firebase_auth import verify_google_token
    import secrets
    
    token = token_data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token required")
        
    decoded_token = verify_google_token(token)
    if not decoded_token:
        raise HTTPException(status_code=401, detail="Invalid Google token")
        
    email = decoded_token.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in token")
        
    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user
        # Generate random password since they use Google auth
        random_password = secrets.token_urlsafe(16)
        new_user = User(
            email=email,
            password_hash=auth.get_password_hash(random_password),
            full_name=decoded_token.get("name", "")
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        user = new_user
        
    # Create JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
