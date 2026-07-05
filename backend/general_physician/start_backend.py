#!/usr/bin/env python3
import subprocess
import sys

# Start the backend
cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
print(f"Starting backend with: {' '.join(cmd)}")
subprocess.run(cmd)
