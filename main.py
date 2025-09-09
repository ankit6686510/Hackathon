"""
Legacy main.py - redirects to new enhanced backend
For backward compatibility, this file imports the new enhanced application
"""

from app.main import app

# Re-export the app for backward compatibility
__all__ = ["app"]

# If run directly, start the server
if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
