from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ExperimentMode = Literal["invent_new", "modify_existing"]


class ExperimentThreadCreateRequest(BaseModel):
    mode: ExperimentMode = "invent_new"
    title: str | None = Field(default=None, min_length=1, max_length=140)
    context_recipe_ids: list[UUID] = Field(default_factory=list)


class ExperimentMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    context_recipe_ids: list[UUID] | None = None
    attach_recipe_names: list[str] | None = None
