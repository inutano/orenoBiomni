"""Schemas for Biomni tool and dataset browser."""

from pydantic import BaseModel, Field


class ToolModule(BaseModel):
    domain: str = Field(..., description="Tool domain (e.g., genomics, cell_biology)")
    name: str = Field(..., description="Module/function name")
    description: str = Field("", description="Description from tool_description or docstring")
    function_count: int = Field(0, description="Number of tool functions in this domain")


class ToolListResponse(BaseModel):
    tools: list[ToolModule]
    total: int


class Dataset(BaseModel):
    name: str = Field(..., description="Dataset filename")
    description: str = Field("", description="Dataset description")
    category: str = Field("data_lake", description="Category: data_lake or library")


class DatasetListResponse(BaseModel):
    datasets: list[Dataset]
    total: int
