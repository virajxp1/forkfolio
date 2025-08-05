# ForkFolio 🍽️

A production-ready recipe management API that transforms raw recipe text into structured, searchable data.

**Key Features:**
- 🤖 AI-powered recipe extraction from messy text/HTML
- 🗄️ Structured database storage with PostgreSQL
- 🔄 Complete processing pipeline with error handling
- 📊 Health monitoring and observability  
- 🚀 Production-ready architecture with connection pooling

V0 design docs:
https://docs.google.com/document/d/1rZlcXuCXt82Ffm7Lrw6L8zqdgDa_wjvsGm_BX-Xw4iI/edit?tab=t.0#heading=h.b8v2kld0jwk5

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL database (Supabase)
- Environment variables configured in `.env`

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd forkfolio

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your database credentials
```

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

## Recipe Processing Pipeline

The core feature of ForkFolio is the **Recipe Processing Pipeline** - a complete system for converting raw, unstructured recipe text into structured data stored in the database.

### Key Endpoint: `/api/v1/process-and-store-recipe`

This endpoint handles messy input like scraped web content, HTML, or poorly formatted text through a three-stage pipeline:

1. **Input Cleanup** - Removes HTML, ads, and navigation elements using LLM
2. **Recipe Extraction** - Extracts structured data (title, ingredients, instructions, timing) using LLM with schema validation  
3. **Database Storage** - Stores recipe with ingredients and instructions in separate tables using database transactions

**Example Usage:**
```bash
curl -X POST "http://localhost:8000/api/v1/process-and-store-recipe" \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Chocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup sugar..."}'
```

For detailed information about the recipe processing flow, see [docs/recipe-processing-flow.md](docs/recipe-processing-flow.md).

## Development

Project Structure:
The project is structured as a FastAPI application with the following components:

```
forkfolio/
├── app/                    # Main application package
│   ├── core/               # Core functionality
│   │   ├── config.py       # Application settings
│   │   ├── dependencies.py # Dependency injection providers
│   │   ├── exceptions.py   # Custom exception hierarchy  
│   │   └── logging.py      # Logging configuration
│   ├── routers/            # API routes
│   │   └── api.py          # Main API router with all endpoints
│   ├── schemas/            # Pydantic models (request/response schemas)
│   ├── services/           # Business logic
│   │   ├── data/           # Data access layer
│   │   │   ├── managers/   # Database managers with context management
│   │   │   └── supabase_client.py  # Connection pooling & transactions
│   │   ├── recipe_extractor_impl.py     # AI recipe extraction
│   │   ├── recipe_input_cleanup_impl.py # Input sanitization
│   │   └── recipe_processing_service.py # Main processing pipeline
│   └── tests/              # Test files
├── docs/                   # Documentation
├── .env                    # Environment variables (not in repo)
├── requirements.txt        # Python dependencies
└── run.py                  # Application runner script
```

## Architecture Highlights

### 🏗️ **Production-Ready Infrastructure**
- **Connection Pooling**: ThreadedConnectionPool (2-20 connections) for optimal database performance
- **Context Managers**: Automatic transaction handling with rollback/commit
- **Custom Exceptions**: Hierarchical error handling with proper exception chaining
- **Dependency Injection**: Clean FastAPI integration with typed providers
- **Health Monitoring**: `/api/v1/health` endpoint with database connectivity checks

### 🔧 **Key Components**
- **RecipeProcessingService**: Main business logic orchestrator
- **RecipeManager**: Database operations with context management  
- **Connection Pool**: Automatic resource management and cleanup
- **Logging System**: Structured logging with configurable levels
- **Exception Hierarchy**: Custom errors for different failure modes

### 📡 **API Endpoints**
- `POST /api/v1/process-and-store-recipe` - Complete recipe processing pipeline
- `GET /api/v1/recipe/{recipe_id}` - Retrieve recipe with ingredients/instructions
- `GET /api/v1/health` - Health check with database connectivity
- `GET /docs` - Interactive API documentation

### 🗄️ **Database Schema**
```sql
-- Core recipe information
recipes (id, title, servings, total_time, source_url, created_at, updated_at)

-- Ordered ingredients list  
recipe_ingredients (id, recipe_id, ingredient_text, order_index)

-- Step-by-step instructions
recipe_instructions (id, recipe_id, instruction_text, step_number)

-- Vector embeddings for similarity search (future)
recipe_embeddings (id, recipe_id, embedding_type, embedding, created_at)
```