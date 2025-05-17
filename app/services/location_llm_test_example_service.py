from typing import Optional

from app.core.test_prompts import CAPITAL_SYSTEM_PROMPT
from app.schemas.location_info import LocationInfo
from app.services.llm_test_service import make_llm_call_text_generation


class LocationLLMTestExampleService:
    """Service for testing LLM-based location processing."""

    def get_capital(self, country: str) -> str:
        """
        Get the capital city of a country.

        Args:
            country: Name of the country

        Returns:
            String containing the capital city name
        """
        user_prompt = f"What is the capital of {country}?"
        return make_llm_call_text_generation(user_prompt, CAPITAL_SYSTEM_PROMPT)

    def get_location_info(self, location_text: str) -> Optional[LocationInfo]:
        """
        Process a location text input and return structured location information.

        Args:
            location_text: A string containing location information to be processed

        Returns:
            LocationInfo object
        """
        pass
