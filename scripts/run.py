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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
