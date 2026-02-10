# ForkFolio 🍽️

A production-ready recipe management API that transforms raw recipe text into structured, searchable data using AI-powered processing pipelines.

**Key Features:**
- 🤖 AI-powered recipe extraction from messy text/HTML
- 🗄️ Structured database storage with PostgreSQL (Supabase)
- 🔄 Complete processing pipeline with error handling
- 📊 Health monitoring and observability  
- 🚀 Production-ready architecture with connection pooling
- 🐳 Containerized deployment with Docker
- 🧪 Comprehensive testing with GitHub Actions CI/CD

V0 design docs:
https://docs.google.com/document/d/1rZlcXuCXt82Ffm7Lrw6L8zqdgDa_wjvsGm_BX-Xw4iI/edit?tab=t.0#heading=h.b8v2kld0jwk5

## Quick Start

### Prerequisites
- Python 3.11+ (recommended)
- PostgreSQL database (Supabase)
- OpenRouter API key for LLM access and embeddings
- pgvector extension enabled in Postgres
- Environment variables configured in `.env`

### Setup

**Option 1: Local Development**
```bash
# Clone the repository
git clone <repository-url>
cd forkfolio

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Create .env file with required variables (see Environment Configuration below)
```

**Option 2: Docker Development**
```bash
# Clone the repository
git clone <repository-url>
cd forkfolio

# Configure environment variables in .env file

# Build and run with Docker Compose
docker-compose up --build
```

## Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration (Required)
SUPABASE_PASSWORD=your_supabase_password

# Optional database password override
DB_PASSWORD=your_database_password

# AI Service Configuration (Required)
OPEN_ROUTER_API_KEY=your_openrouter_api_key

# LLM + embeddings model selection is configured in config/llm.config.ini
# Optional overrides:
# LLM_MODEL_NAME=your_chat_model
# EMBEDDINGS_MODEL_NAME=your_embeddings_model

# Database host/user are configured in config/db.config.ini
```

## Running the Application

**Local Development:**
```bash
# Using the runner script (recommended)
python scripts/run.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Docker:**
```bash
# Using Docker Compose (recommended)
docker-compose -f docker/docker-compose.yml up

# Or build and run manually
docker build -f docker/Dockerfile -t forkfolio .
docker run -p 8000:8000 --env-file .env forkfolio
```

**Access Points:**
- API Server: http://localhost:8000
- Health Check: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Recipe Processing Pipeline

The core feature of ForkFolio is the **Recipe Processing Pipeline** - a complete system for converting raw, unstructured recipe text into structured data stored in the database.

### Key Endpoint: `/api/v1/recipes/process-and-store`

This endpoint handles messy input like scraped web content, HTML, or poorly formatted text through a four-stage pipeline:

1. **Input Cleanup** - Removes HTML, ads, and navigation elements using LLM
2. **Recipe Extraction** - Extracts structured data (title, ingredients, instructions, timing) using LLM with schema validation
3. **Embedding Generation** - Generates embeddings for title + ingredients (OpenRouter)
4. **Database Storage** - Stores recipe, ingredients, instructions, and embeddings in a single transaction

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/recipes/process-and-store" \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Chocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup sugar..."}'
```

For detailed information about the recipe processing flow, see [docs/recipe-processing-flow.md](docs/recipe-processing-flow.md).

## Technology Stack

**Backend Framework:**
- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI web server implementation
- **Pydantic** - Data validation using Python type annotations
- **Python 3.11+** - Latest stable Python version

**Database & Connection Management:**
- **PostgreSQL** - Primary database (via Supabase)
- **psycopg2** - PostgreSQL adapter for Python
- **Connection Pooling** - ThreadedConnectionPool (2-10 connections)
- **Supabase** - Database-as-a-Service with built-in APIs

**AI & Processing:**
- **OpenRouter API** - LLM access for extraction and embeddings
- **Custom Processing Pipeline** - Multi-stage recipe parsing

**Testing & Quality:**
- **pytest** - Testing framework with async support
- **Ruff** - Fast Python linter and formatter
- **pre-commit** - Git hooks for code quality
- **GitHub Actions** - CI/CD pipeline

**Deployment & Infrastructure:**
- **Docker** - Containerization with multi-stage builds
- **Docker Compose** - Local development orchestration
- **Health Checks** - Built-in monitoring endpoints

## Development

### Project Structure
The application follows a clean architecture pattern with clear separation of concerns:

```
forkfolio/
├── app/                    # Main application package
│   ├── core/               # Core functionality & configuration
│   │   ├── config.py       # Application settings & environment variables
│   │   ├── dependencies.py # FastAPI dependency injection providers
│   │   ├── exceptions.py   # Custom exception hierarchy  
│   │   ├── logging.py      # Structured logging configuration
│   │   ├── prompts.py      # LLM prompts for recipe processing
│   │   └── test_*.py       # Core testing utilities
│   ├── routers/            # FastAPI route handlers
│   │   └── api.py          # Main API router with all endpoints
│   ├── schemas/            # Pydantic models for request/response validation
│   │   ├── recipe.py       # Recipe data models
│   │   ├── ingest.py       # Input processing schemas
│   │   └── location_info.py # Location-based data models
│   ├── services/           # Business logic layer
│   │   ├── data/           # Data access layer
│   │   │   ├── managers/   # Database managers with transaction handling
│   │   │   │   ├── base.py # Base database manager
│   │   │   │   └── recipe_manager.py # Recipe-specific database operations
│   │   │   └── supabase_client.py  # Connection pooling & transactions
│   │   ├── llm_generation_service.py   # LLM service abstraction
│   │   ├── recipe_extractor*.py        # AI-powered recipe extraction
│   │   ├── recipe_input_cleanup*.py    # Input sanitization & preprocessing
│   │   └── recipe_processing_service.py # Main orchestration pipeline
│   ├── tests/              # Test suite
│   │   ├── e2e/            # End-to-end integration tests
│   │   └── test_runner.py  # Test execution script
│   └── main.py             # FastAPI application factory
├── .github/workflows/      # GitHub Actions CI/CD
│   ├── test.yml            # Test automation with Supabase connectivity
│   └── lint.yml            # Code quality checks
├── config/                 # Configuration files
│   ├── .pre-commit-config.yaml # Pre-commit hooks configuration
│   ├── pyproject.toml      # Python project configuration
│   └── pytest.ini         # Test configuration
├── docker/                 # Docker-related files
│   ├── Dockerfile          # Multi-stage Docker build
│   ├── docker-compose.yml  # Local development orchestration
│   └── .dockerignore       # Docker ignore patterns
├── docs/                   # Project documentation
├── scripts/                # Executable scripts
│   ├── lint.sh             # Local linting script
│   ├── run.py              # Application runner script
│   └── start_test_server.py # Test server startup script
├── .pre-commit-config.yaml # Pre-commit hooks (symlink to config/)
├── requirements.txt        # Python dependencies
└── .env                    # Environment variables (gitignored)
```

## Architecture Highlights

### 🏗️ **Production-Ready Infrastructure**
- **Connection Pooling**: ThreadedConnectionPool (2-10 connections) with automatic failover
- **Smart Database Routing**: Session Pooler support for GitHub Actions IPv4 compatibility  
- **Context Managers**: Automatic transaction handling with rollback/commit
- **Custom Exceptions**: Hierarchical error handling with proper exception chaining
- **Dependency Injection**: Clean FastAPI integration with typed providers
- **Health Monitoring**: Built-in health checks with database connectivity validation
- **Graceful Shutdown**: Proper resource cleanup on application termination

### 🔧 **Key Components**
- **RecipeProcessingService**: Main business logic orchestrator with error handling
- **RecipeManager**: Database operations with transaction context management  
- **Supabase Client**: Connection pool with automatic resource management
- **LLM Generation Service**: Abstracted AI service integration (OpenRouter)
- **Processing Pipeline**: Multi-stage recipe extraction with validation
- **Logging System**: Structured logging with configurable levels
- **Exception Hierarchy**: Custom errors for different failure modes

### 📡 **API Endpoints**
- `POST /api/v1/recipes/process-and-store` - Complete recipe processing pipeline
- `GET /api/v1/recipes/{recipe_id}` - Retrieve recipe with ingredients/instructions  
- `GET /api/v1/recipes/{recipe_id}/all` - Retrieve recipe with ingredients/instructions/embeddings
- `GET /api/v1/health` - Health check with database connectivity
- `GET /docs` - Interactive Swagger API documentation
- `GET /redoc` - Alternative API documentation format

### 🧪 **Testing Strategy**
- **End-to-End Tests**: Complete pipeline testing with real database connections
- **GitHub Actions CI**: Automated testing on push/PR with IPv4 Supabase compatibility
- **Linting Pipeline**: Ruff-based code formatting and quality checks
- **Pre-commit Hooks**: Automated code quality enforcement
- **Docker Testing**: Containerized test environments

### 🗄️ **Database Schema**
```sql
-- Core recipe information with metadata
recipes (
  id UUID PRIMARY KEY,
  title VARCHAR NOT NULL,
  servings VARCHAR,
  total_time VARCHAR,  -- e.g., "30 minutes", "1 hour"
  source_url VARCHAR,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
)

-- Ordered ingredients list with flexible text storage
recipe_ingredients (
  id UUID PRIMARY KEY,
  recipe_id UUID REFERENCES recipes(id) ON DELETE CASCADE,
  ingredient_text VARCHAR NOT NULL,  -- e.g., "2 cups all-purpose flour"
  order_index INTEGER NOT NULL
)

-- Step-by-step cooking instructions
recipe_instructions (
  id UUID PRIMARY KEY,
  recipe_id UUID REFERENCES recipes(id) ON DELETE CASCADE,
  instruction_text TEXT NOT NULL,
  step_number INTEGER NOT NULL
)

-- Vector embeddings for similarity search and recommendations
recipe_embeddings (
  id UUID PRIMARY KEY,
  recipe_id UUID REFERENCES recipes(id) ON DELETE CASCADE,
  embedding_type VARCHAR NOT NULL,  -- e.g., "title_ingredients"
  embedding VECTOR(768),  -- Vector representation (bge-base-en-v1.5)
  created_at TIMESTAMP DEFAULT NOW()
)
```

## Local Development Commands

```bash
# Code Quality
scripts/lint.sh                     # Run Ruff linter and formatter
pre-commit install                  # Install pre-commit hooks
pre-commit run --all-files          # Run hooks on all files

# Testing
python -m pytest app/tests/e2e/ -v  # Run E2E tests (recommended)
python -m pytest app/tests/ -v      # Run all tests
python app/tests/test_runner.py     # Run using test runner wrapper

# Database
# Health check includes database connectivity test
curl http://localhost:8000/api/v1/health

# Development Server
python scripts/run.py               # Start development server
# or
uvicorn app.main:app --reload       # Alternative server startup
```

## Deployment

**Docker Production:**
```bash
# Build production image
docker build -f docker/Dockerfile -t forkfolio:latest .

# Run with environment variables
docker run -d \
  --name forkfolio \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  forkfolio:latest
```

**Environment-Specific Configuration:**
- Local: Direct Supabase connection
- GitHub Actions: Session Pooler (IPv4 compatibility)  
- Production: Configure `config/db.config.ini` and `SUPABASE_PASSWORD` (or `DB_PASSWORD`)

The application automatically detects Session Pooler usage and adjusts connection parameters accordingly.
