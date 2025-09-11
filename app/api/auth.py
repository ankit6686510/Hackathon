"""
Authentication API endpoints for Google OAuth integration.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.services.auth_service import auth_service
from app.models.auth import User
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

# Pydantic models for request/response
class GoogleLoginRequest(BaseModel):
    token: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None
    access_token: Optional[str] = None
    session_token: Optional[str] = None

class LogoutResponse(BaseModel):
    success: bool
    message: str

class UserResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
    message: str

# Dependency to get database session
def get_db():
    db = next(auth_service.get_db())
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user from JWT token
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current authenticated user from JWT token or session cookie.
    """
    user = None
    
    # Try JWT token first (from Authorization header)
    if credentials:
        try:
            payload = auth_service.verify_jwt_token(credentials.credentials)
            if payload:
                user = db.query(User).filter(User.id == payload["user_id"]).first()
        except Exception as e:
            logger.warning(f"JWT verification failed: {e}")
    
    # Fallback to session token (from cookie)
    if not user and session_token:
        try:
            user = auth_service.get_user_by_session(db, session_token)
        except Exception as e:
            logger.warning(f"Session verification failed: {e}")
    
    return user

# Dependency that requires authentication
async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires user to be authenticated.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    return current_user

@router.post("/google/login", response_model=LoginResponse)
async def google_login(
    request: GoogleLoginRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login with Google OAuth token.
    """
    try:
        # Verify Google token
        user_info = await auth_service.verify_google_token(request.token)
        if not user_info:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        
        # Check if email is verified
        if not user_info.get("email_verified", False):
            raise HTTPException(status_code=400, detail="Email not verified with Google")
        
        # Create or update user
        user = auth_service.create_or_update_user(db, user_info)
        
        # Get client info
        user_agent = http_request.headers.get("user-agent")
        ip_address = http_request.client.host if http_request.client else None
        
        # Create session
        session = auth_service.create_user_session(db, user, user_agent, ip_address)
        
        # Create JWT token
        jwt_token = auth_service.create_jwt_token(user, session)
        
        # Set session cookie (httpOnly for security)
        response.set_cookie(
            key="session_token",
            value=session.session_token,
            max_age=auth_service.session_duration_hours * 3600,  # Convert to seconds
            httponly=True,
            secure=True,  # Use HTTPS in production
            samesite="lax"
        )
        
        logger.info(f"User {user.email} logged in successfully")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            user=user.to_dict(),
            access_token=jwt_token,
            session_token=session.session_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during login")

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    session_token: Optional[str] = Cookie(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current user.
    """
    try:
        if session_token:
            auth_service.logout_user(db, session_token)
        
        # Clear session cookie
        response.delete_cookie(key="session_token")
        
        if current_user:
            logger.info(f"User {current_user.email} logged out successfully")
        
        return LogoutResponse(
            success=True,
            message="Logout successful"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during logout")

@router.post("/logout-all", response_model=LogoutResponse)
async def logout_all_sessions(
    response: Response,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Logout user from all sessions.
    """
    try:
        auth_service.logout_all_sessions(db, current_user.id)
        
        # Clear session cookie
        response.delete_cookie(key="session_token")
        
        logger.info(f"User {current_user.email} logged out from all sessions")
        
        return LogoutResponse(
            success=True,
            message="Logged out from all sessions"
        )
        
    except Exception as e:
        logger.error(f"Logout all error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during logout")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    if not current_user:
        return UserResponse(
            success=False,
            message="Not authenticated"
        )
    
    return UserResponse(
        success=True,
        user=current_user.to_dict(),
        message="User information retrieved successfully"
    )

@router.get("/verify", response_model=UserResponse)
async def verify_authentication(current_user: User = Depends(require_auth)):
    """
    Verify if user is authenticated (protected endpoint).
    """
    return UserResponse(
        success=True,
        user=current_user.to_dict(),
        message="Authentication verified"
    )

@router.post("/cleanup-sessions")
async def cleanup_expired_sessions(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to cleanup expired sessions.
    """
    try:
        # You might want to add admin role check here
        count = auth_service.cleanup_expired_sessions(db)
        
        logger.info(f"Cleaned up {count} expired sessions")
        
        return {
            "success": True,
            "message": f"Cleaned up {count} expired sessions"
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during cleanup")

# Health check endpoint
@router.get("/health")
async def auth_health_check():
    """
    Health check for authentication service.
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": auth_service.SessionLocal().execute("SELECT datetime('now')").scalar()
    }
