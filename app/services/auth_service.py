"""
Enterprise Auth Service v2.0
JWT-based authentication with refresh tokens, token rotation, and blacklisting.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import hashlib

import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_key_change_in_production")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", SECRET_KEY + "_refresh")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory token blacklist (use Redis in production)
_token_blacklist: set = set()
_refresh_tokens: Dict[str, Dict[str, Any]] = {}  # user_id -> token info


class TokenData:
    """Decoded token payload."""
    def __init__(self, username: str, user_id: int, tenant_id: Optional[int], token_type: str, exp: datetime):
        self.username = username
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.token_type = token_type
        self.exp = exp


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def _generate_token_id() -> str:
    """Generate unique token identifier for blacklisting."""
    return secrets.token_hex(16)


def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str]:
    """
    Create a JWT access token.
    
    Returns:
        Tuple of (token, token_id) for tracking
    """
    to_encode = data.copy()
    token_id = _generate_token_id()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": token_id,  # JWT ID for blacklisting
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, token_id


def create_refresh_token(
    user_id: int, 
    username: str,
    expires_delta: Optional[timedelta] = None,
    data: Optional[dict] = None
) -> str:
    """
    Create a refresh token for obtaining new access tokens.
    Refresh tokens are stored server-side for validation and rotation.
    """
    token_id = _generate_token_id()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": username,
        "user_id": user_id,
        "tenant_id": data.get("tenant_id") if isinstance(data, dict) else None,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": token_id,
        "type": "refresh"
    }
    
    # Store refresh token metadata (for rotation/revocation)
    _refresh_tokens[str(user_id)] = {
        "token_id": token_id,
        "expires": expire,
        "created": datetime.utcnow()
    }
    
    return jwt.encode(payload, REFRESH_SECRET_KEY, algorithm=ALGORITHM)


def create_token_pair(user_id: int, username: str, tenant_id: Optional[int] = None) -> Dict[str, str]:
    """
    Create both access and refresh tokens.
    
    Returns:
        Dict with access_token, refresh_token, token_type, expires_in
    """
    access_token, _ = create_access_token(
        data={"sub": username, "user_id": user_id, "tenant_id": tenant_id}
    )
    refresh_token = create_refresh_token(user_id, username, data={"tenant_id": tenant_id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }


def verify_access_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode an access token.
    
    Returns:
        TokenData if valid, None if invalid or blacklisted
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != "access":
            return None
        
        # Check if blacklisted
        token_id = payload.get("jti")
        if token_id and token_id in _token_blacklist:
            return None
        
        username = payload.get("sub")
        user_id = payload.get("user_id")
        exp = datetime.fromtimestamp(payload.get("exp", 0))
        
        if not username:
            return None
            
        return TokenData(
            username=username,
            user_id=user_id or 0,
            tenant_id=payload.get("tenant_id"),
            token_type="access",
            exp=exp
        )
        
    except JWTError:
        return None


def verify_refresh_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a refresh token.
    
    Returns:
        TokenData if valid, None if invalid or revoked
    """
    try:
        payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type
        if payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("user_id")
        token_id = payload.get("jti")
        
        # Verify token is still valid (not rotated)
        stored = _refresh_tokens.get(str(user_id))
        if not stored or stored.get("token_id") != token_id:
            return None
        
        username = payload.get("sub")
        exp = datetime.fromtimestamp(payload.get("exp", 0))
        
        return TokenData(
            username=username,
            user_id=user_id,
            tenant_id=payload.get("tenant_id"),
            token_type="refresh",
            exp=exp
        )
        
    except JWTError:
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Use a refresh token to get a new access token.
    Implements token rotation for security.
    
    Returns:
        New token pair if valid, None if refresh token is invalid
    """
    token_data = verify_refresh_token(refresh_token)
    
    if not token_data:
        return None
    
    # Rotate refresh token (invalidate old, create new)
    # This prevents refresh token reuse attacks
    return create_token_pair(token_data.user_id, token_data.username, token_data.tenant_id)


def revoke_token(token: str, token_type: str = "access") -> bool:
    """
    Revoke a token by adding to blacklist.
    """
    try:
        if token_type == "access":
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        else:
            payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
        
        token_id = payload.get("jti")
        if token_id:
            _token_blacklist.add(token_id)
            
        # For refresh tokens, also remove from active tokens
        if token_type == "refresh":
            user_id = payload.get("user_id")
            if user_id and str(user_id) in _refresh_tokens:
                del _refresh_tokens[str(user_id)]
        
        return True
        
    except JWTError:
        return False


def revoke_all_user_tokens(user_id: int) -> bool:
    """
    Revoke all tokens for a user (logout from all devices).
    """
    # Remove refresh token
    if str(user_id) in _refresh_tokens:
        del _refresh_tokens[str(user_id)]
    
    # Note: Access tokens will naturally expire
    # For immediate revocation, would need to track all issued tokens
    return True


def get_token_info(token: str) -> Optional[Dict[str, Any]]:
    """
    Get decoded token information without full validation.
    Useful for debugging.
    """
    try:
        # Try access token first
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        return {
            "username": payload.get("sub"),
            "user_id": payload.get("user_id"),
            "type": payload.get("type"),
            "expires": datetime.fromtimestamp(payload.get("exp", 0)).isoformat(),
            "issued": datetime.fromtimestamp(payload.get("iat", 0)).isoformat()
        }
    except JWTError:
        try:
            # Try refresh token
            payload = jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            return {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "type": payload.get("type"),
                "expires": datetime.fromtimestamp(payload.get("exp", 0)).isoformat()
            }
        except JWTError:
            return None
