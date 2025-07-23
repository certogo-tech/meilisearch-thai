"""Response models for the Thai tokenizer API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TokenizationResult(BaseModel):
    """Response model for tokenization results."""
    original_text: str = Field(..., description="Original input text")
    tokens: List[str] = Field(..., description="Segmented tokens")
    word_boundaries: List[int] = Field(..., description="Word boundary positions")
    confidence_scores: Optional[List[float]] = Field(None, description="Confidence scores per token")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class DocumentProcessingResult(BaseModel):
    """Response model for document processing."""
    document_id: str = Field(..., description="Document ID")
    status: str = Field(..., description="Processing status")
    tokenized_fields: Dict[str, TokenizationResult] = Field(..., description="Tokenized field results")
    indexed_at: datetime = Field(..., description="Indexing timestamp")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class ConfigurationResponse(BaseModel):
    """Response model for configuration status."""
    status: str = Field(..., description="Configuration status")
    message: str = Field(..., description="Status message")
    applied_at: datetime = Field(..., description="Configuration applied timestamp")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")