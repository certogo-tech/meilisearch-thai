"""
Thai word segmentation module using PyThaiNLP.

This module provides core functionality for segmenting Thai text into meaningful
word components, with special handling for compound words.
"""

import logging
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    from pythainlp import word_tokenize
    from pythainlp.tokenize import Tokenizer
    from pythainlp.corpus.common import thai_words
except ImportError as e:
    raise ImportError(
        "PyThaiNLP is required for Thai tokenization. "
        "Install it with: pip install pythainlp"
    ) from e

from ..utils.logging import get_structured_logger, TokenizationMetrics, performance_monitor


logger = get_structured_logger(__name__)


@dataclass
class TokenizationResult:
    """Result of Thai text tokenization."""
    
    original_text: str
    tokens: List[str]
    word_boundaries: List[int]
    confidence_scores: Optional[List[float]] = None
    processing_time_ms: float = 0.0
    engine: str = "newmm"


class ThaiSegmenter:
    """
    Thai word segmentation engine using PyThaiNLP.
    
    Handles compound word segmentation with multiple tokenization engines
    and provides fallback mechanisms for robust processing.
    """
    
    def __init__(
        self,
        engine: str = "newmm",
        custom_dict: Optional[List[str]] = None,
        keep_whitespace: bool = True
    ):
        """
        Initialize Thai segmenter.
        
        Args:
            engine: Tokenization engine ('newmm', 'attacut', 'deepcut')
            custom_dict: Additional words for custom dictionary
            keep_whitespace: Whether to preserve whitespace in tokenization
        """
        self.engine = engine
        self.keep_whitespace = keep_whitespace
        self.custom_dict = custom_dict or []
        
        # Initialize custom tokenizer if custom dictionary provided
        self._custom_tokenizer = None
        if self.custom_dict:
            try:
                # Create custom word set combining default and custom words
                custom_words = set(thai_words()) | set(self.custom_dict)
                self._custom_tokenizer = Tokenizer(custom_words)
                logger.info(f"Initialized custom tokenizer with {len(custom_words)} words")
            except Exception as e:
                logger.warning(f"Failed to initialize custom tokenizer: {e}")
        
        logger.info("ThaiSegmenter initialized", 
                    engine=engine, 
                    custom_dict_size=len(self.custom_dict),
                    has_custom_tokenizer=self._custom_tokenizer is not None)
    
    @performance_monitor("thai_text_segmentation")
    def segment_text(self, text: str) -> TokenizationResult:
        """
        Segment Thai text into word tokens.
        
        Args:
            text: Input Thai text to segment
            
        Returns:
            TokenizationResult with segmented tokens and metadata
        """
        if not text or not text.strip():
            return TokenizationResult(
                original_text=text,
                tokens=[],
                word_boundaries=[],
                engine=self.engine
            )
        
        start_time = time.time()
        
        try:
            # Use custom tokenizer if available, otherwise use specified engine
            if self._custom_tokenizer:
                # Custom tokenizer doesn't support keep_whitespace parameter
                tokens = self._custom_tokenizer.word_tokenize(text)
                engine_used = f"{self.engine}_custom"
            else:
                tokens = word_tokenize(
                    text,
                    engine=self.engine,
                    keep_whitespace=self.keep_whitespace
                )
                engine_used = self.engine
            
            # Calculate word boundaries
            word_boundaries = self._calculate_boundaries(text, tokens)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Detect compound words and mixed content
            compound_words_detected = sum(1 for token in tokens if len(token) > 6 and self._is_thai_text(token))
            thai_content_ratio = sum(1 for char in text if self._is_thai_char(char)) / len(text) if text else 0
            mixed_content = self._has_mixed_content(text)
            
            result = TokenizationResult(
                original_text=text,
                tokens=tokens,
                word_boundaries=word_boundaries,
                processing_time_ms=processing_time,
                engine=engine_used
            )
            
            # Log structured tokenization metrics
            metrics = TokenizationMetrics(
                text_length=len(text),
                token_count=len(tokens),
                processing_time_ms=processing_time,
                engine=engine_used,
                compound_words_detected=compound_words_detected,
                thai_content_ratio=thai_content_ratio,
                mixed_content=mixed_content,
                fallback_used=False
            )
            logger.tokenization(metrics)
            
            return result
            
        except Exception as e:
            logger.error(f"Tokenization failed with {self.engine}", error=e, 
                        text_length=len(text), engine=self.engine)
            # Fallback to character-level segmentation
            return self._fallback_segmentation(text, start_time)
    
    def segment_compound_words(self, text: str) -> TokenizationResult:
        """
        Specialized segmentation for compound words with enhanced processing.
        
        Args:
            text: Input text potentially containing compound words
            
        Returns:
            TokenizationResult with compound word segmentation
        """
        # First pass with primary engine
        primary_result = self.segment_text(text)
        
        # Check for potential compound words (long tokens)
        compound_candidates = [
            token for token in primary_result.tokens 
            if len(token) > 6 and self._is_thai_text(token)
        ]
        
        if not compound_candidates:
            return primary_result
        
        # Second pass with alternative engine for compound words
        enhanced_tokens = []
        for token in primary_result.tokens:
            if token in compound_candidates:
                # Try alternative segmentation for potential compounds
                sub_result = self._segment_with_fallback(token)
                if len(sub_result.tokens) > 1:
                    enhanced_tokens.extend(sub_result.tokens)
                    logger.debug(f"Split compound word '{token}' into: {sub_result.tokens}")
                else:
                    enhanced_tokens.append(token)
            else:
                enhanced_tokens.append(token)
        
        # Recalculate boundaries for enhanced tokenization
        word_boundaries = self._calculate_boundaries(text, enhanced_tokens)
        
        return TokenizationResult(
            original_text=text,
            tokens=enhanced_tokens,
            word_boundaries=word_boundaries,
            processing_time_ms=primary_result.processing_time_ms,
            engine=f"{primary_result.engine}_compound"
        )
    
    def _segment_with_fallback(self, text: str) -> TokenizationResult:
        """Try alternative engines for better compound word segmentation."""
        fallback_engines = ["attacut", "deepcut", "newmm"]
        
        for engine in fallback_engines:
            if engine == self.engine:
                continue
            
            try:
                tokens = word_tokenize(text, engine=engine, keep_whitespace=False)
                if len(tokens) > 1:  # Successfully split the compound
                    return TokenizationResult(
                        original_text=text,
                        tokens=tokens,
                        word_boundaries=self._calculate_boundaries(text, tokens),
                        engine=engine
                    )
            except Exception as e:
                logger.debug(f"Fallback engine {engine} failed: {e}")
                continue
        
        # Return original if no fallback worked
        return TokenizationResult(
            original_text=text,
            tokens=[text],
            word_boundaries=[0, len(text)],
            engine="fallback"
        )
    
    def _calculate_boundaries(self, text: str, tokens: List[str]) -> List[int]:
        """Calculate character positions of word boundaries."""
        boundaries = [0]
        current_pos = 0
        
        for token in tokens:
            # Find the token in the remaining text
            remaining_text = text[current_pos:]
            token_pos = remaining_text.find(token)
            
            if token_pos >= 0:
                current_pos += token_pos + len(token)
                boundaries.append(current_pos)
            else:
                # Fallback: estimate position
                current_pos += len(token)
                boundaries.append(current_pos)
        
        return boundaries
    
    def _fallback_segmentation(self, text: str, start_time: float) -> TokenizationResult:
        """Fallback to character-level segmentation when tokenization fails."""
        logger.warning("Using character-level fallback segmentation", 
                      text_length=len(text), original_engine=self.engine)
        
        # Simple character-based segmentation preserving Thai characters
        tokens = []
        current_token = ""
        
        for char in text:
            if self._is_thai_char(char):
                current_token += char
            else:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                if char.strip():  # Non-whitespace non-Thai character
                    tokens.append(char)
        
        if current_token:
            tokens.append(current_token)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log fallback metrics
        metrics = TokenizationMetrics(
            text_length=len(text),
            token_count=len(tokens),
            processing_time_ms=processing_time,
            engine="fallback_char",
            compound_words_detected=0,
            thai_content_ratio=sum(1 for char in text if self._is_thai_char(char)) / len(text) if text else 0,
            mixed_content=self._has_mixed_content(text),
            fallback_used=True
        )
        logger.tokenization(metrics)
        
        return TokenizationResult(
            original_text=text,
            tokens=tokens,
            word_boundaries=self._calculate_boundaries(text, tokens),
            processing_time_ms=processing_time,
            engine="fallback_char"
        )
    
    def _is_thai_text(self, text: str) -> bool:
        """Check if text contains primarily Thai characters."""
        if not text:
            return False
        
        thai_chars = sum(1 for char in text if self._is_thai_char(char))
        return thai_chars / len(text) > 0.5
    
    def _is_thai_char(self, char: str) -> bool:
        """Check if character is Thai."""
        return '\u0e00' <= char <= '\u0e7f'
    
    def _has_mixed_content(self, text: str) -> bool:
        """Check if text has mixed Thai/non-Thai content."""
        if not text:
            return False
        thai_chars = sum(1 for char in text if self._is_thai_char(char))
        non_thai_chars = sum(1 for char in text if char.isalnum() and not self._is_thai_char(char))
        return thai_chars > 0 and non_thai_chars > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get segmenter statistics and configuration."""
        return {
            "engine": self.engine,
            "custom_dict_size": len(self.custom_dict),
            "keep_whitespace": self.keep_whitespace,
            "has_custom_tokenizer": self._custom_tokenizer is not None
        }