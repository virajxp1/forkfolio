from pydantic import BaseModel, Field


# Request model for ingestion
class RecipeIngestionRequest(BaseModel):
    raw_input: str = Field(..., description="Raw unstructured recipe input")
