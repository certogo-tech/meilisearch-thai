"""
Token processing utilities for MeiliSearch integration.

This module provides functions to convert segmented Thai words into 
MeiliSearch-compatible tokens with custom separators and handles mixed content.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .thai_segmenter import TokenizationResult


logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type classification for processing."""
    THAI = "thai"
    ENGLISH = "english"
    NUMERIC = "numeric"
    PUNCTUATION = "punctuation"
    WHITESPACE = "whitespace"
    MIXED = "mixed"


@dataclass
class ProcessedToken:
    """Processed token with metadata for MeiliSearch."""
    
    original: str
    processed: str
    content_type: ContentType
    is_compound: bool = False
    sub_tokens: Optional[List[str]] = None
    separator_positions: Optional[List[int]] = None


@dataclass
class TokenProcessingResult:
    """Result of token processing for MeiliSearch integration."""
    
    original_text: str
    processed_text: str
    tokens: List[ProcessedToken]
    meilisearch_separators: List[str]
    processing_metadata: Dict[str, Any]


class TokenProcessor:
    """
    Processes segmented Thai tokens for MeiliSearch compatibility.
    
    Handles custom separator insertion, mixed content processing,
    and MeiliSearch-specific token formatting.
    """
    
    # Thai word boundary separator (invisible separator)
    THAI_WORD_SEPARATOR = "​"  # U+200B Zero Width Space
    THAI_COMPOUND_SEPARATOR = "​​"  # Double zero width space for compounds
    
    # MeiliSearch separator tokens
    DEFAULT_SEPARATORS = [
        " ", "\t", "\n", "\r",  # Standard whitespace
        ".", ",", ";", ":", "!", "?",  # Punctuation
        "(", ")", "[", "]", "{", "}",  # Brackets
        "-", "_", "/", "\\", "|",  # Symbols
        THAI_WORD_SEPARATOR,  # Thai word boundaries
        THAI_COMPOUND_SEPARATOR  # Thai compound boundaries
    ]
    
    def __init__(
        self,
        custom_separators: Optional[List[str]] = None,
        preserve_original: bool = True,
        handle_compounds: bool = True
    ):
        """
        Initialize token processor.
        
        Args:
            custom_separators: Additional separator tokens
            preserve_original: Whether to preserve original text
            handle_compounds: Whether to process compound words specially
        """
        self.custom_separators = custom_separators or []
        self.preserve_original = preserve_original
        self.handle_compounds = handle_compounds
        
        # Combine default and custom separators
        self.separators = list(set(self.DEFAULT_SEPARATORS + self.custom_separators))
        
        logger.info(f"TokenProcessor initialized with {len(self.separators)} separators")
    
    def process_tokenization_result(
        self, 
        tokenization_result: TokenizationResult
    ) -> TokenProcessingResult:
        """
        Process tokenization result for MeiliSearch compatibility.
        
        Args:
            tokenization_result: Result from Thai segmentation
            
        Returns:
            TokenProcessingResult with MeiliSearch-compatible tokens
        """
        if not tokenization_result.tokens:
            return TokenProcessingResult(
                original_text=tokenization_result.original_text,
                processed_text=tokenization_result.original_text,
                tokens=[],
                meilisearch_separators=self.separators,
                processing_metadata={"empty_input": True}
            )
        
        processed_tokens = []
        processed_text_parts = []
        
        for token in tokenization_result.tokens:
            processed_token = self._process_single_token(token)
            processed_tokens.append(processed_token)
            processed_text_parts.append(processed_token.processed)
        
        processed_text = "".join(processed_text_parts)
        
        metadata = {
            "original_token_count": len(tokenization_result.tokens),
            "processed_token_count": len(processed_tokens),
            "thai_tokens": sum(1 for t in processed_tokens if t.content_type == ContentType.THAI),
            "compound_tokens": sum(1 for t in processed_tokens if t.is_compound),
            "processing_engine": tokenization_result.engine,
            "processing_time_ms": tokenization_result.processing_time_ms
        }
        
        return TokenProcessingResult(
            original_text=tokenization_result.original_text,
            processed_text=processed_text,
            tokens=processed_tokens,
            meilisearch_separators=self.separators,
            processing_metadata=metadata
        )
    
    def process_mixed_content(self, text: str) -> TokenProcessingResult:
        """
        Process mixed Thai-English content with appropriate separators.
        
        Args:
            text: Mixed content text
            
        Returns:
            TokenProcessingResult with mixed content processing
        """
        # Split text into segments by content type
        segments = self._segment_mixed_content(text)
        
        processed_tokens = []
        processed_text_parts = []
        
        for segment_text, content_type in segments:
            if content_type == ContentType.THAI:
                # Process Thai segments with word segmentation
                from .thai_segmenter import ThaiSegmenter
                segmenter = ThaiSegmenter()
                thai_result = segmenter.segment_text(segment_text)
                
                for token in thai_result.tokens:
                    processed_token = self._process_single_token(token)
                    processed_tokens.append(processed_token)
                    processed_text_parts.append(processed_token.processed)
            else:
                # Process non-Thai segments as single tokens
                processed_token = self._process_single_token(segment_text)
                processed_tokens.append(processed_token)
                processed_text_parts.append(processed_token.processed)
        
        processed_text = "".join(processed_text_parts)
        
        metadata = {
            "mixed_content": True,
            "segment_count": len(segments),
            "content_types": [ct.value for _, ct in segments]
        }
        
        return TokenProcessingResult(
            original_text=text,
            processed_text=processed_text,
            tokens=processed_tokens,
            meilisearch_separators=self.separators,
            processing_metadata=metadata
        )
    
    def _process_single_token(self, token: str) -> ProcessedToken:
        """Process a single token for MeiliSearch compatibility."""
        if not token or not token.strip():
            return ProcessedToken(
                original=token,
                processed=token,
                content_type=ContentType.WHITESPACE
            )
        
        content_type = self._classify_content_type(token)
        
        # Handle Thai tokens with word boundary separators
        if content_type == ContentType.THAI:
            processed, is_compound, sub_tokens = self._process_thai_token(token)
            
            return ProcessedToken(
                original=token,
                processed=processed,
                content_type=content_type,
                is_compound=is_compound,
                sub_tokens=sub_tokens,
                separator_positions=self._find_separator_positions(processed)
            )
        
        # Handle non-Thai tokens
        else:
            # Add appropriate separators around non-Thai content
            if content_type in [ContentType.ENGLISH, ContentType.NUMERIC]:
                # Ensure word boundaries around English/numeric content
                processed = f" {token} "
            else:
                processed = token
            
            return ProcessedToken(
                original=token,
                processed=processed,
                content_type=content_type
            )
    
    def _process_thai_token(self, token: str) -> Tuple[str, bool, Optional[List[str]]]:
        """
        Process Thai token with compound word handling.
        
        Returns:
            Tuple of (processed_token, is_compound, sub_tokens)
        """
        if not self.handle_compounds or len(token) <= 4:
            # Simple Thai token - add word boundary separator
            return f"{token}{self.THAI_WORD_SEPARATOR}", False, None
        
        # Check if token might be a compound word
        if self._is_potential_compound(token):
            # Try to split compound word
            sub_tokens = self._split_compound_word(token)
            
            if len(sub_tokens) > 1:
                # Process as compound with special separators
                processed_parts = []
                for i, sub_token in enumerate(sub_tokens):
                    processed_parts.append(sub_token)
                    if i < len(sub_tokens) - 1:
                        processed_parts.append(self.THAI_COMPOUND_SEPARATOR)
                
                processed_parts.append(self.THAI_WORD_SEPARATOR)
                processed = "".join(processed_parts)
                
                return processed, True, sub_tokens
        
        # Regular Thai token
        return f"{token}{self.THAI_WORD_SEPARATOR}", False, None
    
    def _classify_content_type(self, token: str) -> ContentType:
        """Classify token content type."""
        if not token.strip():
            return ContentType.WHITESPACE
        
        # Count character types
        thai_chars = sum(1 for c in token if self._is_thai_char(c))
        english_chars = sum(1 for c in token if c.isalpha() and not self._is_thai_char(c))
        numeric_chars = sum(1 for c in token if c.isdigit())
        punct_chars = sum(1 for c in token if not c.isalnum() and not c.isspace())
        
        total_chars = len(token.strip())
        
        if total_chars == 0:
            return ContentType.WHITESPACE
        
        # Count how many different types are present
        type_counts = [
            (thai_chars, ContentType.THAI),
            (english_chars, ContentType.ENGLISH),
            (numeric_chars, ContentType.NUMERIC),
            (punct_chars, ContentType.PUNCTUATION)
        ]
        
        # Filter out zero counts
        present_types = [(count, ctype) for count, ctype in type_counts if count > 0]
        
        # If multiple types are present with significant counts, it's mixed
        if len(present_types) > 1:
            # Check if any type dominates (>50%)
            max_count, max_type = max(present_types, key=lambda x: x[0])
            if max_count / total_chars > 0.5:
                return max_type
            else:
                return ContentType.MIXED
        
        # Single type present
        elif len(present_types) == 1:
            return present_types[0][1]
        
        # Fallback
        else:
            return ContentType.MIXED
    
    def _segment_mixed_content(self, text: str) -> List[Tuple[str, ContentType]]:
        """Segment mixed content by content type."""
        segments = []
        current_segment = ""
        current_type = None
        
        for char in text:
            char_type = self._classify_content_type(char)
            
            if char_type == ContentType.WHITESPACE:
                # Add whitespace to current segment or as separate segment
                if current_segment:
                    current_segment += char
                else:
                    segments.append((char, char_type))
                continue
            
            if current_type is None or current_type == char_type:
                # Continue current segment
                current_segment += char
                current_type = char_type
            else:
                # Start new segment
                if current_segment:
                    segments.append((current_segment, current_type))
                current_segment = char
                current_type = char_type
        
        # Add final segment
        if current_segment:
            segments.append((current_segment, current_type))
        
        return segments
    
    def _is_potential_compound(self, token: str) -> bool:
        """Check if token might be a compound word."""
        # Simple heuristics for compound detection
        return (
            len(token) > 6 and  # Long enough to be compound
            self._is_thai_text(token) and  # Primarily Thai
            not self._is_common_long_word(token)  # Not a known long word
        )
    
    def _split_compound_word(self, token: str) -> List[str]:
        """Attempt to split compound word into components."""
        # This is a simplified approach - in practice, you might use
        # more sophisticated compound word detection
        
        # Try to split at common compound boundaries
        potential_splits = []
        
        # Look for common Thai compound patterns
        compound_patterns = [
            r'(การ.+)',  # การ + word
            r'(.+ความ.+)',  # word + ความ + word
            r'(.+โรง.+)',  # word + โรง + word
            r'(.+ศาสตร์)',  # word + ศาสตร์
        ]
        
        for pattern in compound_patterns:
            match = re.match(pattern, token)
            if match:
                # Simple split - in practice, use more sophisticated methods
                mid_point = len(token) // 2
                return [token[:mid_point], token[mid_point:]]
        
        # Fallback: return as single token
        return [token]
    
    def _is_common_long_word(self, token: str) -> bool:
        """Check if token is a known long word (not compound)."""
        # List of common long Thai words that shouldn't be split
        long_words = {
            "สวัสดีครับ", "สวัสดีค่ะ", "ขอบคุณครับ", "ขอบคุณค่ะ",
            "ประเทศไทย", "กรุงเทพมหานคร", "มหาวิทยาลัย"
        }
        return token in long_words
    
    def _find_separator_positions(self, text: str) -> List[int]:
        """Find positions of separators in processed text."""
        positions = []
        for i, char in enumerate(text):
            if char in self.separators:
                positions.append(i)
        return positions
    
    def _is_thai_char(self, char: str) -> bool:
        """Check if character is Thai."""
        return '\u0e00' <= char <= '\u0e7f'
    
    def _is_thai_text(self, text: str) -> bool:
        """Check if text is primarily Thai."""
        if not text:
            return False
        thai_chars = sum(1 for char in text if self._is_thai_char(char))
        return thai_chars / len(text) > 0.5
    
    def get_meilisearch_settings(self) -> Dict[str, Any]:
        """
        Get MeiliSearch settings for Thai tokenization.
        
        Returns:
            Dictionary with MeiliSearch tokenization settings
        """
        return {
            "separatorTokens": self.separators,
            "nonSeparatorTokens": [
                "ๆ",  # Thai repetition mark
                "ฯ",  # Thai abbreviation mark
                "ฯลฯ",  # Thai et cetera
                "'", "'",  # Smart quotes
                """, """,  # Smart double quotes
            ],
            "dictionary": [],  # Can be populated with custom terms
            "synonyms": {},  # Can be populated with Thai synonyms
            "stopWords": [
                # Common Thai stop words
                "และ", "หรือ", "แต่", "เพราะ", "ถ้า", "เมื่อ",
                "ใน", "บน", "ที่", "จาก", "ไป", "มา",
                "เป็น", "คือ", "มี", "ได้", "จะ", "ต้อง"
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics and configuration."""
        return {
            "separator_count": len(self.separators),
            "custom_separators": self.custom_separators,
            "preserve_original": self.preserve_original,
            "handle_compounds": self.handle_compounds,
            "thai_word_separator": repr(self.THAI_WORD_SEPARATOR),
            "compound_separator": repr(self.THAI_COMPOUND_SEPARATOR)
        }