"""Request models for the Thai tokenizer API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TokenizeRequest(BaseModel):
    """Request model for text tokenization."""
    text: str = Field(..., description="Thai text to tokenize")
    include_confidence: bool = Field(False, description="Include confidence scores")


class IndexDocumentRequest(BaseModel):
    """Request model for document indexing."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MeiliSearchConfigRequest(BaseModel):
    """Request model for MeiliSearch configuration."""
    host: str = Field(..., description="MeiliSearch host URL")
    api_key: str = Field(..., description="MeiliSearch API key")
    index_name: str = Field(..., description="Index name")


class TokenizerConfigRequest(BaseModel):
    """Request model for tokenizer configuration."""
    engine: str = Field("newmm", description="Tokenization engine (pythainlp, newmm, attacut, deepcut)")
    model_version: Optional[str] = Field(None, description="Model version")
    custom_dictionary: Optional[List[str]] = Field(None, description="Custom dictionary words")
    keep_whitespace: bool = Field(True, description="Whether to preserve whitespace in tokenization")
    handle_compounds: bool = Field(True, description="Whether to apply compound word processing")
    fallback_engine: Optional[str] = Field("newmm", description="Fallback engine if primary fails")
    batch_size: int = Field(100, description="Batch processing size")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_ms: int = Field(5000, description="Timeout in milliseconds")