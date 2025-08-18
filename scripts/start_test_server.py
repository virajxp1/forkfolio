#!/usr/bin/env python3
"""
Simple script to start the server for testing.
"""

import os
import sys
import uvicorn

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

if __name__ == "__main__":
    # Change to project root directory
    os.chdir(project_root)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
