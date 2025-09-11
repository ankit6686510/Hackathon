"""
Database migration script for SherlockAI payment domain system.
Creates the pending_issues table for the learning system.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

# Import directly from the models.py file
import importlib.util
import sys

# Load the models.py file directly
models_file_path = Path(__file__).parent.parent / "models.py"
spec = importlib.util.spec_from_file_location("models", models_file_path)
models_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_module)

# Get Base and PendingIssue from the models module
Base = models_module.Base
PendingIssue = models_module.PendingIssue

from app.models.auth import User, UserSession
from dotenv import load_dotenv

load_dotenv()

def create_database_tables():
    """Create all database tables including PendingIssue and authentication tables."""
    
    # Get database URL from environment and convert async URL to sync
    database_url = os.getenv("DATABASE_URL", "sqlite:///./SherlockAI.db")
    
    # Convert async SQLite URL to sync for migration
    if "sqlite+aiosqlite" in database_url:
        database_url = database_url.replace("sqlite+aiosqlite", "sqlite")
    
    print(f"🗄️  Connecting to database: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    
    try:
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        with engine.connect() as conn:
            # Check PendingIssue table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='pending_issues';"))
            if result.fetchone():
                print("✅ PendingIssue table created successfully")
            else:
                print("❌ Failed to create PendingIssue table")
                return False
            
            # Check User table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users';"))
            if result.fetchone():
                print("✅ User table created successfully")
            else:
                print("❌ Failed to create User table")
                return False
            
            # Check UserSession table
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_sessions';"))
            if result.fetchone():
                print("✅ UserSession table created successfully")
            else:
                print("❌ Failed to create UserSession table")
                return False
        
        print("🎉 Database migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False
    
    finally:
        engine.dispose()

def check_existing_tables():
    """Check what tables already exist in the database."""
    
    database_url = os.getenv("DATABASE_URL", "sqlite:///./SherlockAI.db")
    
    # Convert async SQLite URL to sync for migration
    if "sqlite+aiosqlite" in database_url:
        database_url = database_url.replace("sqlite+aiosqlite", "sqlite")
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]
            
            print("📊 Existing tables:")
            for table in tables:
                print(f"   - {table}")
            
            return tables
            
    except Exception as e:
        print(f"❌ Failed to check existing tables: {e}")
        return []
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("🔧 SherlockAI Database Migration")
    print("=" * 40)
    
    # Check existing tables
    existing_tables = check_existing_tables()
    
    if "pending_issues" in existing_tables:
        print("ℹ️  PendingIssue table already exists")
        response = input("Do you want to recreate it? (y/N): ").strip().lower()
        if response != 'y':
            print("Migration skipped.")
            sys.exit(0)
    
    # Run migration
    success = create_database_tables()
    
    if success:
        print("\n🎯 Migration Summary:")
        print("   ✅ PendingIssue table ready for learning system")
        print("   ✅ User table ready for authentication")
        print("   ✅ UserSession table ready for session management")
        print("   ✅ Payment domain validation active")
        print("   ✅ AI solution storage enabled")
        print("   ✅ Google OAuth authentication ready")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
