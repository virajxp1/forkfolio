from uuid import UUID

from pydantic import BaseModel, Field


class ExperimentThreadCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=140)
    context_recipe_ids: list[UUID] = Field(default_factory=list)
    is_test: bool = False
    include_test_data: bool = False


class ExperimentMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    context_recipe_ids: list[UUID] | None = None
    attach_recipe_ids: list[UUID] | None = None
    attach_recipe_names: list[str] | None = None
    include_test_data: bool = False
