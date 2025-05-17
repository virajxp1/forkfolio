from pydantic import BaseModel, Field


class LocationInfo(BaseModel):
    """
    Information about a location including its country and highlights.
    """

    location: str = Field(..., description="The name of the city or location.")
    country: str = Field(..., description="The country where the location is situated.")
    highlights: str = Field(
        ...,
        description="Description of key attractions or highlights.",
    )
