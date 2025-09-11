#!/usr/bin/env python3
"""
Quick setup script for SherlockAI hackathon demo
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def print_banner():
    print("""
🔍 SherlockAI - Quick Setup Script
==================================
AI-Powered Issue Intelligence System for Juspay
""")

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required. Current version:", sys.version)
        return False
    print("✅ Python version:", sys.version.split()[0])
    return True

def check_env_file():
    """Check if .env file exists and has required keys"""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        print("📝 Creating .env from template...")
        
        # Copy from .env.example if it exists
        example_path = Path(".env.example")
        if example_path.exists():
            with open(example_path, 'r') as f:
                content = f.read()
            with open(env_path, 'w') as f:
                f.write(content)
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env and add your API keys:")
            print("   - GEMINI_API_KEY")
            print("   - PINECONE_API_KEY")
            return False
        else:
            print("❌ .env.example not found")
            return False
    
    # Check for required keys
    required_keys = ["GEMINI_API_KEY", "PINECONE_API_KEY"]
    missing_keys = []
    
    with open(env_path, 'r') as f:
        content = f.read()
        for key in required_keys:
            if f"{key}=" not in content or f"{key}=your_" in content:
                missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing API keys in .env: {', '.join(missing_keys)}")
        print("📝 Please edit .env and add your API keys")
        return False
    
    print("✅ .env file configured")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Failed to install dependencies:", e.stderr.decode())
        return False

def setup_vector_database():
    """Setup vector database with embeddings"""
    print("🔄 Setting up vector database...")
    try:
        subprocess.run([sys.executable, "embedder.py"], check=True, capture_output=True)
        print("✅ Vector database setup complete")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Failed to setup vector database:", e.stderr.decode())
        print("💡 Make sure your API keys are correct in .env")
        return False

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting backend server...")
    try:
        # Start backend in background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ])
        
        # Wait for backend to start
        print("⏳ Waiting for backend to start...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get("http://localhost:8000/api/v1/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Backend is running at http://localhost:8000")
                    return process
            except:
                pass
            time.sleep(1)
            print(f"   Waiting... ({i+1}/30)")
        
        print("❌ Backend failed to start within 30 seconds")
        process.terminate()
        return None
        
    except Exception as e:
        print("❌ Failed to start backend:", str(e))
        return None

def start_frontend():
    """Start the Streamlit frontend"""
    print("🎨 Starting frontend...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped")
    except Exception as e:
        print("❌ Failed to start frontend:", str(e))

def main():
    """Main setup function"""
    print_banner()
    
    # Check prerequisites
    if not check_python_version():
        return False
    
    if not check_env_file():
        print("\n🔧 Please configure your .env file and run this script again")
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Setup vector database
    if not setup_vector_database():
        print("\n💡 You can skip this step for now and run 'python embedder.py' later")
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        return False
    
    print("\n🎉 Setup complete!")
    print("📊 Backend API: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/v1/health")
    print("\n🎨 Starting frontend...")
    print("🌐 Frontend will be available at: http://localhost:8501")
    print("\n⚠️  Press Ctrl+C to stop both services")
    
    try:
        # Start frontend (this will block)
        start_frontend()
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
    finally:
        if backend_process:
            backend_process.terminate()
            print("✅ Backend stopped")
    
    print("👋 SherlockAI demo stopped")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
