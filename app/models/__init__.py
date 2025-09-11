"""
Models package for SherlockAI.
"""

# Import models using importlib to avoid circular imports
import importlib.util
import sys
from pathlib import Path

# Load the models.py file directly
models_file_path = Path(__file__).parent.parent / "models.py"
spec = importlib.util.spec_from_file_location("app_models", models_file_path)
models_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_module)

# Import from auth models
from .auth import User, UserSession

# Export models from the loaded module
Base = models_module.Base
Issue = models_module.Issue
SearchLog = models_module.SearchLog
Feedback = models_module.Feedback
FeedbackLog = models_module.FeedbackLog
PendingIssue = models_module.PendingIssue
APIKey = models_module.APIKey
IssueBase = models_module.IssueBase
IssueCreate = models_module.IssueCreate
IssueUpdate = models_module.IssueUpdate
IssueResponse = models_module.IssueResponse
SearchRequest = models_module.SearchRequest
SearchResult = models_module.SearchResult
SearchResponse = models_module.SearchResponse
FeedbackCreate = models_module.FeedbackCreate
FeedbackResponse = models_module.FeedbackResponse
UserCreate = models_module.UserCreate
UserResponse = models_module.UserResponse
Token = models_module.Token
HealthCheck = models_module.HealthCheck
MetricsResponse = models_module.MetricsResponse
IssueStatus = models_module.IssueStatus
SearchType = models_module.SearchType

# Export all models
__all__ = [
    'Base', 'Issue', 'SearchLog', 'Feedback', 'FeedbackLog', 
    'PendingIssue', 'APIKey', 'IssueBase', 'IssueCreate', 'IssueUpdate',
    'IssueResponse', 'SearchRequest', 'SearchResult', 'SearchResponse',
    'FeedbackCreate', 'FeedbackResponse', 'UserCreate', 'UserResponse',
    'Token', 'HealthCheck', 'MetricsResponse', 'IssueStatus', 'SearchType',
    'User', 'UserSession'
]
