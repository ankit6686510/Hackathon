"""
Authentication service for Google OAuth integration.
"""

import os
import jwt
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.auth import User, UserSession
import secrets
import hashlib

class AuthService:
    def __init__(self):
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.jwt_algorithm = "HS256"
        self.session_duration_hours = 24 * 7  # 7 days
        
        # Database setup
        database_url = os.getenv("DATABASE_URL", "sqlite:///./sherlockai.db")
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db(self):
        """Get database session."""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    async def verify_google_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Google OAuth token and return user info.
        """
        try:
            print(f"🔍 Verifying Google token with client_id: {self.google_client_id}")
            
            # Verify token with Google
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
                )
                
                print(f"📡 Google API response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Google API returned error: {response.text}")
                    return None
                
                token_info = response.json()
                print(f"📋 Token info received: {token_info}")
                
                # Verify the token is for our app
                token_aud = token_info.get("aud")
                print(f"🔑 Token audience: {token_aud}")
                print(f"🔑 Expected client_id: {self.google_client_id}")
                
                if token_aud != self.google_client_id:
                    print(f"❌ Audience mismatch: {token_aud} != {self.google_client_id}")
                    return None
                
                # Extract user information
                user_info = {
                    "google_id": token_info.get("sub"),
                    "email": token_info.get("email"),
                    "name": token_info.get("name"),
                    "picture": token_info.get("picture"),
                    "given_name": token_info.get("given_name"),
                    "family_name": token_info.get("family_name"),
                    "email_verified": token_info.get("email_verified", False)
                }
                
                print(f"✅ User info extracted: {user_info}")
                return user_info
                
        except Exception as e:
            print(f"💥 Error verifying Google token: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_or_update_user(self, db: Session, user_info: Dict[str, Any]) -> User:
        """
        Create a new user or update existing user from Google OAuth info.
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.google_id == user_info["google_id"]).first()
        
        if existing_user:
            # Update existing user
            existing_user.email = user_info["email"]
            existing_user.name = user_info["name"]
            existing_user.picture = user_info.get("picture")
            existing_user.given_name = user_info.get("given_name")
            existing_user.family_name = user_info.get("family_name")
            existing_user.updated_at = datetime.utcnow()
            existing_user.last_login = datetime.utcnow()
            
            db.commit()
            db.refresh(existing_user)
            return existing_user
        else:
            # Create new user
            new_user = User(
                google_id=user_info["google_id"],
                email=user_info["email"],
                name=user_info["name"],
                picture=user_info.get("picture"),
                given_name=user_info.get("given_name"),
                family_name=user_info.get("family_name"),
                last_login=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
    
    def generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def create_user_session(self, db: Session, user: User, user_agent: str = None, ip_address: str = None) -> UserSession:
        """
        Create a new user session.
        """
        session_token = self.generate_session_token()
        expires_at = datetime.utcnow() + timedelta(hours=self.session_duration_hours)
        
        # Deactivate old sessions for this user (optional - for single session per user)
        # db.query(UserSession).filter(UserSession.user_id == user.id).update({"is_active": False})
        
        new_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session
    
    def create_jwt_token(self, user: User, session: UserSession) -> str:
        """
        Create JWT token for the user session.
        """
        payload = {
            "user_id": user.id,
            "session_id": session.id,
            "email": user.email,
            "name": user.name,
            "exp": session.expires_at,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload.
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_by_session(self, db: Session, session_token: str) -> Optional[User]:
        """
        Get user by session token.
        """
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            return None
        
        user = db.query(User).filter(User.id == session.user_id).first()
        return user
    
    def logout_user(self, db: Session, session_token: str) -> bool:
        """
        Logout user by deactivating session.
        """
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if session:
            session.is_active = False
            db.commit()
            return True
        
        return False
    
    def logout_all_sessions(self, db: Session, user_id: str) -> bool:
        """
        Logout user from all sessions.
        """
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
        
        db.commit()
        return True
    
    def cleanup_expired_sessions(self, db: Session) -> int:
        """
        Clean up expired sessions.
        """
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired_sessions)
        
        for session in expired_sessions:
            db.delete(session)
        
        db.commit()
        return count

# Global auth service instance
auth_service = AuthService()
