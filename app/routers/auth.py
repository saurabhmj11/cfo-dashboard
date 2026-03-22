"""
Enterprise Auth Router v2.0
OAuth 2.0 compatible authentication with refresh tokens.
"""
from datetime import timedelta
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import schemas, db_models
from app.services import auth_service, tenant_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response Models
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


# ============== Endpoints ==============

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    """
    # Check for existing username
    db_user = db.query(db_models.User).filter(db_models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check for existing email
    if user.email:
        db_email = db.query(db_models.User).filter(db_models.User.email == user.email).first()
        if db_email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth_service.get_password_hash(user.password)
    
    # Simple Auto-Tenant Logic: Create a tenant for the new user if none exists
    # In a real SaaS, this might be a separate "Organization Creation" flow
    tenant_name = f"{user.username}_org"
    db_tenant = tenant_service.get_tenant_by_name(db, tenant_name)
    if not db_tenant:
        db_tenant = tenant_service.create_tenant(db, schemas.TenantCreate(name=tenant_name))
    
    new_user = db_models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        tenant_id=db_tenant.id,
        role="USER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/token", response_model=TokenResponse)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login.
    Returns access_token and refresh_token.
    """
    user = db.query(db_models.User).filter(db_models.User.username == form_data.username).first()
    
    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token pair with tenant_id
    tokens = auth_service.create_token_pair(user.id, user.username, user.tenant_id)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"]
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.
    Implements token rotation for security.
    """
    new_tokens = auth_service.refresh_access_token(request.refresh_token)
    
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return TokenResponse(
        access_token=new_tokens["access_token"],
        refresh_token=new_tokens["refresh_token"],
        token_type=new_tokens["token_type"],
        expires_in=new_tokens["expires_in"]
    )


@router.post("/logout")
def logout(
    request: LogoutRequest,
    current_user: db_models.User = Depends(get_current_user)
):
    """
    Logout and revoke tokens.
    """
    # Revoke refresh token if provided
    if request.refresh_token:
        auth_service.revoke_token(request.refresh_token, "refresh")
    
    # Revoke all user tokens
    auth_service.revoke_all_user_tokens(current_user.id)
    
    return {"status": "success", "message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all_devices(current_user: db_models.User = Depends(get_current_user)):
    """
    Logout from all devices by revoking all tokens.
    """
    auth_service.revoke_all_user_tokens(current_user.id)
    return {"status": "success", "message": "Logged out from all devices"}


@router.get("/me", response_model=schemas.User)
def get_current_user_info(current_user: db_models.User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return current_user


@router.post("/verify")
def verify_token(current_user: db_models.User = Depends(get_current_user)):
    """
    Verify that the current token is valid.
    Useful for frontend to check auth status.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }


# ============== Password Management ==============

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(
    request: PasswordChangeRequest,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for current user.
    """
    # Verify current password
    if not auth_service.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password (basic rules)
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    
    # Update password
    current_user.hashed_password = auth_service.get_password_hash(request.new_password)
    db.commit()
    
    # Revoke all existing tokens (force re-login)
    auth_service.revoke_all_user_tokens(current_user.id)
    
    return {"status": "success", "message": "Password changed successfully. Please login again."}
