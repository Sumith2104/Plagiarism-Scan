from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core import auth
from app.models.user import User
from app.core.config import settings

router = APIRouter()

@router.post("/login", response_model=dict)
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=dict)
def register_user(
    email: str, 
    password: str, 
    full_name: str = None,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    new_user = User(
        email=email,
        password_hash=auth.get_password_hash(password),
        full_name=full_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"id": new_user.id, "email": new_user.email, "message": "User registered successfully"}

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
