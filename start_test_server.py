#!/usr/bin/env python3
"""
Simple script to start the server for testing.
"""
import sys
import uvicorn

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
