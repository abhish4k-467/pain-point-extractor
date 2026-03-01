from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

class Review(BaseModel):
    text: str = Field(description="The full text of the review")
    rating: int = Field(description="The star rating, 1-5")

class FeatureRequest(BaseModel):
    category: str = Field(description="A short category name for the feature request (e.g., 'Performance', 'UI/UX', 'Billing')")
    description: str = Field(description="A detailed description of the requested feature based on the pain point")
    source_reviews: List[str] = Field(description="List of review snippets that triggered this request")
    priority: Literal["High", "Medium", "Low"] = Field(description="Priority: must be exactly 'High', 'Medium', or 'Low'")

    @field_validator("source_reviews", mode="before")
    @classmethod
    def coerce_source_reviews(cls, v):
        """Coerce all items to strings (LLM sometimes returns ints)."""
        if isinstance(v, list):
            return [str(item) for item in v]
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v):
        """Accept any casing: 'high' -> 'High', 'LOW' -> 'Low', etc."""
        if isinstance(v, str):
            return v.capitalize()
        return v

class ExtractedData(BaseModel):
    reviews: List[Review]
    feature_requests: List[FeatureRequest]
