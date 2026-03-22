"""
Enterprise Dependencies v2.0
Authentication, authorization, and rate limiting dependencies.
"""
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.services import auth_service
from app.models import schemas, db_models
from app.database import get_db
from datetime import datetime
from collections import defaultdict
import time

# OAuth2 password bearer scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Session = Depends(get_db)
) -> db_models.User:
    """
    Get the currently authenticated user.
    Uses the new auth_service for token verification.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Verify token using new auth service
    token_data = auth_service.verify_access_token(token)
    
    if not token_data:
        raise credentials_exception
    
    # Get user from database
    user = db.query(db_models.User).filter(
        db_models.User.username == token_data.username
    ).first()
    
    if user is None:
        raise credentials_exception
    
    return user
    
def get_current_tenant_id(
    current_user: db_models.User = Depends(get_current_user)
) -> Optional[int]:
    """
    Extract tenant_id from current user.
    Enforces isolation by providing a standard way to get the active tenant.
    """
    return current_user.tenant_id


def get_current_user_optional(
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)],
    db: Session = Depends(get_db)
) -> Optional[db_models.User]:
    """
    Get current user if authenticated, None otherwise.
    Useful for endpoints that work differently for authenticated users.
    """
    if not token:
        return None
    
    token_data = auth_service.verify_access_token(token)
    if not token_data:
        return None
    
    return db.query(db_models.User).filter(
        db_models.User.username == token_data.username
    ).first()


def require_role(allowed_roles: list[str]):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(["ADMIN"]))])
    """
    def role_checker(current_user: db_models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {allowed_roles}"
            )
        return current_user
    return role_checker


# ============== Rate Limiting ==============

class RateLimiter:
    """
    In-memory rate limiter.
    In production, use Redis for distributed rate limiting.
    """
    
    def __init__(self):
        # Format: {client_id: [(timestamp, endpoint), ...]}
        self._requests: dict = defaultdict(list)
        self._cleanup_interval = 60  # seconds
        self._last_cleanup = time.time()
    
    def _cleanup(self):
        """Remove old entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff = now - 3600  # Keep last hour
        for client_id in list(self._requests.keys()):
            self._requests[client_id] = [
                r for r in self._requests[client_id]
                if r[0] > cutoff
            ]
            if not self._requests[client_id]:
                del self._requests[client_id]
        
        self._last_cleanup = now
    
    def check_rate_limit(
        self, 
        client_id: str, 
        endpoint: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            (is_allowed, remaining_requests)
        """
        self._cleanup()
        
        now = time.time()
        cutoff = now - window_seconds
        key = f"{client_id}:{endpoint}"
        
        # Count recent requests
        recent = [r for r in self._requests[key] if r[0] > cutoff]
        
        if len(recent) >= limit:
            return False, 0
        
        # Record this request
        self._requests[key].append((now, endpoint))
        remaining = limit - len(recent) - 1
        
        return True, remaining


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(
    limit: int = 60,
    window_seconds: int = 60,
    by: str = "ip"  # "ip" or "user"
):
    """
    Rate limiting dependency factory.
    
    Usage:
        @router.get("/data", dependencies=[Depends(rate_limit(limit=10, window_seconds=60))])
    
    Args:
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
        by: Rate limit by "ip" or "user"
    """
    async def rate_limit_check(
        request: Request,
        current_user: Optional[db_models.User] = Depends(get_current_user_optional)
    ):
        # Determine client identifier
        if by == "user" and current_user:
            client_id = f"user:{current_user.id}"
        else:
            # Use IP address
            forwarded = request.headers.get("X-Forwarded-For")
            client_id = f"ip:{forwarded.split(',')[0] if forwarded else request.client.host}"
        
        endpoint = request.url.path
        
        allowed, remaining = _rate_limiter.check_rate_limit(
            client_id, endpoint, limit, window_seconds
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {window_seconds} seconds.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + window_seconds)
                }
            )
        
        # Add rate limit headers to response (would need middleware for this)
        return {"remaining": remaining}
    
    return rate_limit_check


# ============== Common Rate Limits ==============

# Strict limit for sensitive endpoints
rate_limit_strict = rate_limit(limit=10, window_seconds=60)

# Standard API limit
rate_limit_standard = rate_limit(limit=60, window_seconds=60)

# Generous limit for read operations
rate_limit_generous = rate_limit(limit=120, window_seconds=60)
