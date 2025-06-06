from ..core.prompts import CLEANUP_SYSTEM_PROMPT
from .llm_generation_service import make_llm_call_text_generation
from .recipe_input_cleanup import RecipeInputCleanup


class RecipeInputCleanupServiceImpl(RecipeInputCleanup):
    """
    Implementation of RecipeInputCleanup that uses LLM to clean messy input data.

    This class takes messy scraped content (HTML, ads, navigation, etc.)
    and returns clean text focusing on recipe content only.
    """

    def __init__(self, minimum_valid_text_length: int = 50):
        """
        Initialize the cleanup service.

        Args:
            minimum_valid_text_length: Minimum character count for valid cleaned
                                     output. Defaults to 50 characters.
        """
        self.minimum_valid_text_length = minimum_valid_text_length
        # TODO: Add LLM client initialization here

    def cleanup_input(self, messy_input: str) -> str:
        """
        Clean up messy input data using LLM processing.

        Args:
            messy_input: Raw input string that may contain HTML, ads, navigation
                        elements, or other unwanted content

        Returns:
            Cleaned string containing only recipe-related content

        Raises:
            ValueError: If the LLM output is invalid or empty
        """
        user_prompt = f"Please clean up this messy recipe data:\n\n{messy_input}"
        cleaned_text = make_llm_call_text_generation(user_prompt, CLEANUP_SYSTEM_PROMPT)

        if self._validate_cleaned_output(cleaned_text):
            return cleaned_text
        else:
            raise ValueError(
                f"LLM failed to produce valid cleaned output. "
                f"Got: {cleaned_text[:100]}..."
            )

    def _validate_cleaned_output(self, cleaned_text: str) -> bool:
        """
        Validate that the cleaned output is reasonable.

        Args:
            cleaned_text: The cleaned text from LLM

        Returns:
            True if output appears valid, False otherwise
        """
        # Basic validation: check it's not empty and has sufficient content
        stripped_text = cleaned_text.strip()
        return (
            bool(stripped_text) and len(stripped_text) >= self.minimum_valid_text_length
        )
