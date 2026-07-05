#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Set up Python path to include the project
project_root = Path("/app/backend/general_physician")
sys.path.insert(0, str(project_root))

print("Starting backend initialization...")

# Try to load environment from different locations
env_paths = [
    project_root.parent / ".env",
    project_root / ".env",
    Path("/app/.env")
]

for env_path in env_paths:
    if env_path.exists():
        print(f"Loading environment from: {env_path}")
        from dotenv import load_dotenv
        load_dotenv(env_path)
        break
else:
    print("WARNING: .env file not found in any expected location")

print(f"POSTGRES_HOST: {os.environ.get('POSTGRES_HOST', 'NOT_SET')}")
print(f"POSTGRES_PORT: {os.environ.get('POSTGRES_PORT', 'NOT_SET')}")
print(f"NVIDIA_API_KEY: {'SET' if 'NVIDIA_API_KEY' in os.environ else 'NOT_SET'}")

# Try to initialize the FastAPI app
try:
    from main import app
    print("✓ FastAPI app imported successfully")
    
    # Test a simple request handler
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/health")
    print(f"Health endpoint status: {response.status_code}")
    
    # Test register endpoint with proper validation data
    response = client.post("/register", json={
        "name": "Test Patient",
        "phone": "9999999999",
        "consent": True
    })
    print(f"Register endpoint status: {response.status_code}")
    if response.status_code != 200:
        print(f"Register response: {response.text}")
        
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("Backend initialization complete")
