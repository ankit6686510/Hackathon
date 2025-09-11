"""
Database models for SherlockAI API
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from enum import Enum

Base = declarative_base()


class IssueStatus(str, Enum):
    """Issue status enumeration"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SearchType(str, Enum):
    """Search type enumeration"""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


# Database Models
class Issue(Base):
    """Issue model for storing historical issues"""
    __tablename__ = "issues"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    resolution = Column(Text)
    status = Column(String, default=IssueStatus.OPEN)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    priority = Column(String, default="medium")
    category = Column(String, nullable=True)
    
    # Relationships
    searches = relationship("SearchLog", back_populates="issue")
    feedback = relationship("Feedback", back_populates="issue")


class User(Base):
    """User model for authentication and tracking"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    searches = relationship("SearchLog", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")


class SearchLog(Base):
    """Search log model for analytics and monitoring"""
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(Text, nullable=False)
    search_type = Column(String, default=SearchType.SEMANTIC)
    top_k = Column(Integer, default=3)
    results_count = Column(Integer, default=0)
    execution_time_ms = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Top result for quick analysis
    top_result_id = Column(String, ForeignKey("issues.id"), nullable=True)
    top_result_score = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="searches")
    issue = relationship("Issue", back_populates="searches")


class Feedback(Base):
    """Feedback model for AI suggestion improvement"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    issue_id = Column(String, ForeignKey("issues.id"), nullable=False)
    search_query = Column(Text, nullable=False)
    feedback_type = Column(String, nullable=False)  # positive, negative
    rating = Column(Integer, nullable=True)  # 1-5 scale
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    issue = relationship("Issue", back_populates="feedback")


class FeedbackLog(Base):
    """Feedback log model for analytics"""
    __tablename__ = "feedback_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    result_id = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 scale
    feedback_text = Column(Text, nullable=True)
    helpful = Column(Boolean, nullable=False)
    timestamp = Column(DateTime, default=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


class PendingIssue(Base):
    """Pending issue model for learning system"""
    __tablename__ = "pending_issues"
    
    id = Column(String, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    ai_solution = Column(Text, nullable=False)
    payment_score = Column(Integer, default=0)
    confidence_level = Column(Float, default=0.0)
    status = Column(String, default="pending_verification")  # pending_verification, verified, rejected
    created_at = Column(DateTime, default=func.now())
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)
    actual_resolution = Column(Text, nullable=True)
    effectiveness_score = Column(Float, nullable=True)  # How effective was the AI solution
    
    # Payment domain metadata
    payment_type = Column(String, nullable=True)  # UPI, card, wallet, etc.
    bank_involved = Column(String, nullable=True)
    error_code = Column(String, nullable=True)


class APIKey(Base):
    """API key model for external integrations"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    rate_limit = Column(Integer, default=1000)  # requests per hour


# Pydantic Models for API
class IssueBase(BaseModel):
    """Base issue schema"""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    resolution: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: str = Field(default="medium")
    category: Optional[str] = None


class IssueCreate(IssueBase):
    """Schema for creating issues"""
    id: str = Field(..., min_length=1, max_length=50)


class IssueUpdate(BaseModel):
    """Schema for updating issues"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    resolution: Optional[str] = None
    status: Optional[IssueStatus] = None
    tags: Optional[List[str]] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    resolved_by: Optional[str] = None


class IssueResponse(IssueBase):
    """Schema for issue responses"""
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Schema for search requests"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)
    search_type: SearchType = Field(default=SearchType.SEMANTIC)
    include_resolved_only: bool = Field(default=True)
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    filters: Optional[dict] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Schema for individual search results"""
    id: str
    title: str
    description: str
    resolution: Optional[str] = None
    ai_suggestion: str
    score: float
    tags: List[str]
    created_at: datetime
    resolved_by: Optional[str] = None


class SearchResponse(BaseModel):
    """Schema for search responses"""
    query: str
    results: List[SearchResult]
    total_results: int
    execution_time_ms: float
    search_type: SearchType
    timestamp: datetime


class FeedbackCreate(BaseModel):
    """Schema for creating feedback"""
    issue_id: str
    search_query: str
    feedback_type: str = Field(..., pattern="^(positive|negative)$")
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Schema for feedback responses"""
    id: int
    issue_id: str
    feedback_type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Schema for creating users"""
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """Schema for user responses"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication tokens"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class HealthCheck(BaseModel):
    """Schema for health check responses"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    services: dict


class MetricsResponse(BaseModel):
    """Schema for metrics responses"""
    total_searches: int
    total_issues: int
    total_users: int
    avg_response_time_ms: float
    top_queries: List[dict]
    recent_feedback: List[dict]
