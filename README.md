# Forkfolio

Designed to be your recipe book, explorer and adaptor for investment portfolios.

V0 design docs:
https://docs.google.com/document/d/1rZlcXuCXt82Ffm7Lrw6L8zqdgDa_wjvsGm_BX-Xw4iI/edit?tab=t.0#heading=h.b8v2kld0jwk5

## Project Structure


## Running the Application

Run the application with:

```bash
python run.py
```

Or use uvicorn directly:

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

Project Structure:
The project is structured as a FastAPI application with the following components:

```
forkfolio/
├── app/                    # Main application package
│   ├── core/               # Core functionality (settings, dependencies)
│   ├── models/             # Database models
│   ├── routers/            # API routes
│   ├── schemas/            # Pydantic models (request/response schemas)
│   ├── services/           # Business logic
│   └── tests/              # Test files
├── .env                    # Environment variables
├── .gitignore              # Git ignore file
├── main.py                 # Entry point for compatibility
├── requirements.txt        # Python dependencies
└── run.py                  # Application runner script
```

  1. Configuration Files:
    - requirements.txt - Lists all Python dependencies
    - .env - Environment variables for configuration
    - .gitignore - Standard Python gitignore file
    - run.py - Convenient script to start the application
  2. Key Files:
    - app/main.py - Main FastAPI application definition
    - app/core/config.py - Settings using Pydantic for type validation
    - app/routers/api.py - API router with versioning support
  3. FastAPI Features:
    - API versioning via prefix (/api/v1)
    - Health check endpoint (/health)
    - Swagger UI docs automatically set up (/docs)