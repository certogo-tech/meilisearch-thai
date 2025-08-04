"""
Query processing service for Thai search proxy.

This module handles query tokenization, variant generation, and optimization
for Thai language search queries with mixed content support.
"""

import asyncio
import re
import time
from typing import List, Dict, Any, Optional, Tuple

from ...tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult as ThaiTokenizationResult
from ...utils.logging import get_structured_logger
from ..models.query import (
    ProcessedQuery, 
    QueryVariant, 
    QueryVariantType, 
    TokenizationResult
)
from ..config.settings import SearchProxySettings


logger = get_structured_logger(__name__)


class QueryProcessor:
    """
    Query processor that integrates with Thai tokenization engines.
    
    Handles query analysis, tokenization with multiple strategies,
    and generation of optimized query variants for search execution.
    """
    
    def __init__(self, settings: SearchProxySettings):
        """
        Initialize the query processor.
        
        Args:
            settings: Configuration settings for the search proxy
        """
        self.settings = settings
        self._thai_segmenter = None
        self._fallback_segmenters: Dict[str, ThaiSegmenter] = {}
        self._initialized = False
        
        # Thai character range for detection
        self._thai_char_range = (0x0e00, 0x0e7f)
        
        # English word pattern for mixed content detection
        self._english_word_pattern = re.compile(r'[a-zA-Z]+')
        
    async def initialize(self) -> None:
        """Initialize the query processor and tokenization engines."""
        if self._initialized:
            return
            
        start_time = time.time()
        
        try:
            # Initialize primary Thai segmenter
            self._thai_segmenter = ThaiSegmenter(
                engine=self.settings.tokenization.primary_engine,
                keep_whitespace=True
            )
            
            # Initialize fallback segmenters
            for engine in self.settings.tokenization.fallback_engines:
                if engine != self.settings.tokenization.primary_engine:
                    self._fallback_segmenters[engine] = ThaiSegmenter(
                        engine=engine,
                        keep_whitespace=True
                    )
            
            self._initialized = True
            
            initialization_time = (time.time() - start_time) * 1000
            logger.info(
                "Query processor initialized",
                primary_engine=self.settings.tokenization.primary_engine,
                fallback_engines=list(self._fallback_segmenters.keys()),
                initialization_time_ms=initialization_time
            )
            
        except Exception as e:
            logger.error("Failed to initialize query processor", error=str(e))
            raise RuntimeError(f"Query processor initialization failed: {str(e)}")
    
    async def process_query(self, query: str) -> ProcessedQuery:
        """
        Process a search query through the complete tokenization pipeline.
        
        Args:
            query: Raw search query text
            
        Returns:
            ProcessedQuery with tokenization results and query variants
            
        Raises:
            RuntimeError: If processor is not initialized
            ValueError: If query is invalid
        """
        if not self._initialized:
            raise RuntimeError("Query processor not initialized")
        
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        start_time = time.time()
        
        try:
            # Analyze query characteristics
            query_analysis = self._analyze_query(query)
            
            # Perform tokenization with multiple strategies
            tokenization_results = await self._tokenize_with_strategies(query, query_analysis)
            
            # Generate query variants from tokenization results
            query_variants = self._generate_query_variants(query, tokenization_results, query_analysis)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Create processed query result
            processed_query = ProcessedQuery(
                original_query=query,
                tokenization_results=tokenization_results,
                query_variants=query_variants,
                processing_time_ms=processing_time,
                thai_content_detected=query_analysis["thai_content_detected"],
                mixed_content=query_analysis["mixed_content"],
                primary_language=query_analysis["primary_language"],
                fallback_used=any(result.engine.endswith("_fallback") for result in tokenization_results)
            )
            
            # Log processing metrics
            logger.info(
                "Query processed successfully",
                query_length=len(query),
                thai_content_ratio=query_analysis["thai_content_ratio"],
                mixed_content=query_analysis["mixed_content"],
                tokenization_results_count=len(tokenization_results),
                query_variants_count=len(query_variants),
                processing_time_ms=processing_time,
                primary_language=query_analysis["primary_language"]
            )
            
            return processed_query
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(
                "Query processing failed",
                query_length=len(query),
                error=str(e),
                processing_time_ms=processing_time
            )
            
            # Return fallback processed query
            return await self._create_fallback_processed_query(query, processing_time)
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query characteristics for processing strategy selection.
        
        Args:
            query: Input query text
            
        Returns:
            Dictionary with query analysis results
        """
        # Count Thai characters
        thai_char_count = sum(
            1 for char in query 
            if self._thai_char_range[0] <= ord(char) <= self._thai_char_range[1]
        )
        
        # Count English words
        english_matches = self._english_word_pattern.findall(query)
        english_char_count = sum(len(match) for match in english_matches)
        
        # Calculate ratios
        total_chars = len(query.replace(' ', ''))  # Exclude spaces from count
        thai_content_ratio = thai_char_count / total_chars if total_chars > 0 else 0.0
        english_content_ratio = english_char_count / total_chars if total_chars > 0 else 0.0
        
        # Determine content characteristics
        thai_content_detected = thai_content_ratio > 0.1
        english_content_detected = english_content_ratio > 0.1
        mixed_content = thai_content_detected and english_content_detected
        
        # Determine primary language
        if thai_content_ratio > english_content_ratio:
            primary_language = "thai"
        elif english_content_ratio > thai_content_ratio:
            primary_language = "english"
        else:
            primary_language = "mixed"
        
        return {
            "thai_char_count": thai_char_count,
            "english_char_count": english_char_count,
            "thai_content_ratio": thai_content_ratio,
            "english_content_ratio": english_content_ratio,
            "thai_content_detected": thai_content_detected,
            "english_content_detected": english_content_detected,
            "mixed_content": mixed_content,
            "primary_language": primary_language,
            "total_length": len(query)
        }
    
    async def _tokenize_with_strategies(
        self, 
        query: str, 
        query_analysis: Dict[str, Any]
    ) -> List[TokenizationResult]:
        """
        Tokenize query using multiple strategies based on content analysis.
        
        Args:
            query: Input query text
            query_analysis: Results from query analysis
            
        Returns:
            List of tokenization results from different engines
        """
        tokenization_results = []
        
        # Skip tokenization for non-Thai content
        if not query_analysis["thai_content_detected"]:
            logger.debug("No Thai content detected, skipping tokenization")
            return tokenization_results
        
        # Primary tokenization
        try:
            primary_result = await asyncio.wait_for(
                self._tokenize_with_engine(query, self._thai_segmenter),
                timeout=self.settings.tokenization.timeout_ms / 1000
            )
            
            if primary_result.success and primary_result.confidence >= self.settings.tokenization.confidence_threshold:
                tokenization_results.append(primary_result)
                logger.debug(f"Primary tokenization successful with {primary_result.engine}")
            else:
                logger.warning(f"Primary tokenization failed or low confidence: {primary_result.confidence}")
                
        except asyncio.TimeoutError:
            logger.warning(f"Primary tokenization timed out after {self.settings.tokenization.timeout_ms}ms")
        except Exception as e:
            logger.warning(f"Primary tokenization failed: {str(e)}")
        
        # Fallback tokenization if primary failed or for compound word splitting
        if (not tokenization_results or 
            self.settings.tokenization.enable_compound_splitting):
            
            for engine_name, segmenter in self._fallback_segmenters.items():
                try:
                    fallback_result = await asyncio.wait_for(
                        self._tokenize_with_engine(query, segmenter, is_fallback=True),
                        timeout=self.settings.tokenization.timeout_ms / 1000
                    )
                    
                    if fallback_result.success:
                        tokenization_results.append(fallback_result)
                        logger.debug(f"Fallback tokenization successful with {engine_name}")
                        
                        # Stop after first successful fallback unless compound splitting is enabled
                        if not self.settings.tokenization.enable_compound_splitting:
                            break
                            
                except asyncio.TimeoutError:
                    logger.debug(f"Fallback tokenization with {engine_name} timed out")
                except Exception as e:
                    logger.debug(f"Fallback tokenization with {engine_name} failed: {str(e)}")
        
        # If all tokenization failed, create character-level fallback
        if not tokenization_results:
            logger.warning("All tokenization strategies failed, using character-level fallback")
            char_level_result = self._create_character_level_tokenization(query)
            tokenization_results.append(char_level_result)
        
        return tokenization_results
    
    async def _tokenize_with_engine(
        self, 
        query: str, 
        segmenter: ThaiSegmenter, 
        is_fallback: bool = False
    ) -> TokenizationResult:
        """
        Tokenize query with a specific engine.
        
        Args:
            query: Input query text
            segmenter: Thai segmenter instance
            is_fallback: Whether this is a fallback tokenization
            
        Returns:
            TokenizationResult with tokenization outcome
        """
        start_time = time.time()
        
        try:
            # Use compound word segmentation if enabled
            if self.settings.tokenization.enable_compound_splitting:
                thai_result = segmenter.segment_compound_words(query)
            else:
                thai_result = segmenter.segment_text(query)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Calculate confidence based on tokenization quality
            confidence = self._calculate_tokenization_confidence(query, thai_result)
            
            engine_name = thai_result.engine
            if is_fallback:
                engine_name += "_fallback"
            
            return TokenizationResult(
                engine=engine_name,
                tokens=thai_result.tokens,
                processing_time_ms=processing_time,
                confidence=confidence,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            
            return TokenizationResult(
                engine=f"{segmenter.engine}_failed",
                tokens=[],
                processing_time_ms=processing_time,
                confidence=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_tokenization_confidence(
        self, 
        original_query: str, 
        thai_result: ThaiTokenizationResult
    ) -> float:
        """
        Calculate confidence score for tokenization result.
        
        Args:
            original_query: Original query text
            thai_result: Tokenization result from ThaiSegmenter
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not thai_result.tokens:
            return 0.0
        
        # Base confidence factors
        confidence_factors = []
        
        # Factor 1: Token count reasonableness (not too many, not too few)
        token_count = len(thai_result.tokens)
        query_length = len(original_query.replace(' ', ''))
        
        if query_length > 0:
            tokens_per_char = token_count / query_length
            # Optimal range: 0.1 to 0.5 tokens per character
            if 0.1 <= tokens_per_char <= 0.5:
                confidence_factors.append(1.0)
            elif tokens_per_char < 0.1:
                confidence_factors.append(tokens_per_char / 0.1)
            else:
                confidence_factors.append(max(0.1, 1.0 - (tokens_per_char - 0.5) / 0.5))
        
        # Factor 2: Processing time (faster is generally better for confidence)
        processing_time_factor = max(0.1, 1.0 - (thai_result.processing_time_ms / 1000))
        confidence_factors.append(processing_time_factor)
        
        # Factor 3: Token quality (avoid single character tokens for Thai)
        thai_tokens = [token for token in thai_result.tokens if self._is_thai_text(token)]
        if thai_tokens:
            avg_thai_token_length = sum(len(token) for token in thai_tokens) / len(thai_tokens)
            # Prefer tokens with length 2-6 characters
            if 2 <= avg_thai_token_length <= 6:
                confidence_factors.append(1.0)
            elif avg_thai_token_length < 2:
                confidence_factors.append(avg_thai_token_length / 2)
            else:
                confidence_factors.append(max(0.3, 1.0 - (avg_thai_token_length - 6) / 10))
        
        # Calculate weighted average confidence
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5  # Default confidence
    
    def _create_character_level_tokenization(self, query: str) -> TokenizationResult:
        """
        Create character-level tokenization as last resort fallback.
        
        Args:
            query: Input query text
            
        Returns:
            TokenizationResult with character-level tokens
        """
        start_time = time.time()
        
        # Simple character-level tokenization preserving Thai characters
        tokens = []
        current_token = ""
        
        for char in query:
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
        
        return TokenizationResult(
            engine="character_level_fallback",
            tokens=tokens,
            processing_time_ms=processing_time,
            confidence=0.3,  # Low confidence for character-level
            success=True,
            error_message=None
        )
    
    def _generate_query_variants(
        self, 
        original_query: str, 
        tokenization_results: List[TokenizationResult],
        query_analysis: Dict[str, Any]
    ) -> List[QueryVariant]:
        """
        Generate optimized query variants from tokenization results.
        
        Args:
            original_query: Original search query
            tokenization_results: Results from tokenization engines
            query_analysis: Query analysis results
            
        Returns:
            List of optimized query variants for search execution
        """
        variants = []
        seen_queries = set()  # Track duplicate queries
        
        # Always include original query if configured
        if self.settings.tokenization.preserve_original:
            original_variant = self._create_original_variant(original_query, query_analysis)
            variants.append(original_variant)
            seen_queries.add(original_query.strip().lower())
        
        # Generate variants from tokenization results
        for result in tokenization_results:
            if not result.success or not result.tokens:
                continue
            
            # Generate multiple variants from single tokenization result
            result_variants = self._generate_variants_from_tokenization(
                result, query_analysis, original_query
            )
            
            # Add unique variants
            for variant in result_variants:
                query_key = variant.query_text.strip().lower()
                if query_key not in seen_queries:
                    variants.append(variant)
                    seen_queries.add(query_key)
        
        # Generate fallback variants if no successful tokenization
        if not any(result.success for result in tokenization_results):
            fallback_variants = self._generate_fallback_variants(original_query, query_analysis)
            for variant in fallback_variants:
                query_key = variant.query_text.strip().lower()
                if query_key not in seen_queries:
                    variants.append(variant)
                    seen_queries.add(query_key)
        
        # Optimize variant selection and weights
        variants = self._optimize_variant_selection(variants, query_analysis)
        
        # Limit number of variants to prevent performance issues
        max_variants = self.settings.search.max_query_variants
        if len(variants) > max_variants:
            # Sort by weight and keep top variants
            variants.sort(key=lambda v: v.weight, reverse=True)
            variants = variants[:max_variants]
            
            logger.debug(f"Limited query variants to {max_variants} (from {len(variants)})")
        
        return variants
    
    def _create_original_variant(
        self, 
        original_query: str, 
        query_analysis: Dict[str, Any]
    ) -> QueryVariant:
        """Create the original query variant with optimized weight."""
        base_weight = self._calculate_variant_weight(QueryVariantType.ORIGINAL, query_analysis)
        
        # Boost original query weight for non-Thai content
        if not query_analysis["thai_content_detected"]:
            base_weight *= 1.2
        
        return QueryVariant(
            query_text=original_query,
            variant_type=QueryVariantType.ORIGINAL,
            tokenization_engine="none",
            weight=min(1.0, base_weight),
            search_options=self._get_search_options_for_variant(QueryVariantType.ORIGINAL),
            metadata={
                "is_original": True,
                "query_length": len(original_query),
                "thai_content_ratio": query_analysis["thai_content_ratio"],
                "mixed_content": query_analysis["mixed_content"]
            }
        )
    
    def _generate_variants_from_tokenization(
        self, 
        result: TokenizationResult, 
        query_analysis: Dict[str, Any],
        original_query: str
    ) -> List[QueryVariant]:
        """Generate multiple variants from a single tokenization result."""
        variants = []
        
        # Standard tokenized variant
        tokenized_query = " ".join(result.tokens)
        
        # Skip if identical to original
        if tokenized_query.strip() == original_query.strip():
            return variants
        
        # Determine variant type based on engine and content
        variant_type = self._determine_variant_type(result, query_analysis)
        
        # Create main tokenized variant
        main_variant = QueryVariant(
            query_text=tokenized_query,
            variant_type=variant_type,
            tokenization_engine=result.engine,
            weight=self._calculate_variant_weight(variant_type, query_analysis, result.confidence),
            search_options=self._get_search_options_for_variant(variant_type),
            metadata={
                "token_count": len(result.tokens),
                "tokenization_confidence": result.confidence,
                "processing_time_ms": result.processing_time_ms,
                "original_engine": result.engine.replace("_fallback", "").replace("_compound", ""),
                "avg_token_length": sum(len(token) for token in result.tokens) / len(result.tokens)
            }
        )
        variants.append(main_variant)
        
        # Generate additional variants for compound words
        if self.settings.tokenization.enable_compound_splitting and len(result.tokens) > 1:
            compound_variants = self._generate_compound_variants(result, query_analysis)
            variants.extend(compound_variants)
        
        # Generate phrase variants for multi-token results
        if len(result.tokens) > 2:
            phrase_variants = self._generate_phrase_variants(result, query_analysis)
            variants.extend(phrase_variants)
        
        return variants
    
    def _generate_compound_variants(
        self, 
        result: TokenizationResult, 
        query_analysis: Dict[str, Any]
    ) -> List[QueryVariant]:
        """Generate variants optimized for compound word searches."""
        variants = []
        
        # Create variant with compound words joined
        compound_tokens = []
        for token in result.tokens:
            if len(token) > 3 and self._is_thai_text(token):
                # Keep longer Thai tokens as compounds
                compound_tokens.append(token)
            else:
                compound_tokens.append(token)
        
        if len(compound_tokens) != len(result.tokens):
            compound_query = " ".join(compound_tokens)
            
            variant = QueryVariant(
                query_text=compound_query,
                variant_type=QueryVariantType.COMPOUND_SPLIT,
                tokenization_engine=f"{result.engine}_compound",
                weight=self._calculate_variant_weight(
                    QueryVariantType.COMPOUND_SPLIT, 
                    query_analysis, 
                    result.confidence * 0.9  # Slightly lower confidence for compound
                ),
                search_options=self._get_search_options_for_variant(QueryVariantType.COMPOUND_SPLIT),
                metadata={
                    "compound_optimization": True,
                    "original_token_count": len(result.tokens),
                    "compound_token_count": len(compound_tokens)
                }
            )
            variants.append(variant)
        
        return variants
    
    def _generate_phrase_variants(
        self, 
        result: TokenizationResult, 
        query_analysis: Dict[str, Any]
    ) -> List[QueryVariant]:
        """Generate phrase-based variants for better matching."""
        variants = []
        
        # Create quoted phrase variant for exact phrase matching
        if len(result.tokens) > 2:
            phrase_query = f'"{" ".join(result.tokens)}"'
            
            variant = QueryVariant(
                query_text=phrase_query,
                variant_type=QueryVariantType.TOKENIZED,
                tokenization_engine=f"{result.engine}_phrase",
                weight=self._calculate_variant_weight(
                    QueryVariantType.TOKENIZED, 
                    query_analysis, 
                    result.confidence * 0.8  # Lower weight for phrase matching
                ),
                search_options={
                    **self._get_search_options_for_variant(QueryVariantType.TOKENIZED),
                    "matching_strategy": "all"  # Require all terms for phrases
                },
                metadata={
                    "phrase_matching": True,
                    "phrase_length": len(result.tokens)
                }
            )
            variants.append(variant)
        
        return variants
    
    def _generate_fallback_variants(
        self, 
        original_query: str, 
        query_analysis: Dict[str, Any]
    ) -> List[QueryVariant]:
        """Generate fallback variants when tokenization fails."""
        variants = []
        
        # Character-level fallback for Thai content
        if query_analysis["thai_content_detected"]:
            char_tokens = self._create_character_level_tokens(original_query)
            if char_tokens:
                char_query = " ".join(char_tokens)
                
                variant = QueryVariant(
                    query_text=char_query,
                    variant_type=QueryVariantType.FALLBACK,
                    tokenization_engine="character_fallback",
                    weight=0.4,  # Low weight for character-level fallback
                    search_options={
                        "matching_strategy": "last",
                        "typo_tolerance": {"enabled": True, "min_word_size_for_typo": 2}
                    },
                    metadata={
                        "fallback_type": "character_level",
                        "char_token_count": len(char_tokens)
                    }
                )
                variants.append(variant)
        
        # Word-level fallback for mixed content
        if query_analysis["mixed_content"]:
            word_tokens = original_query.split()
            if len(word_tokens) > 1:
                word_query = " ".join(word_tokens)
                
                variant = QueryVariant(
                    query_text=word_query,
                    variant_type=QueryVariantType.FALLBACK,
                    tokenization_engine="word_split_fallback",
                    weight=0.6,
                    search_options={
                        "matching_strategy": "last",
                        "typo_tolerance": {"enabled": True}
                    },
                    metadata={
                        "fallback_type": "word_split",
                        "word_count": len(word_tokens)
                    }
                )
                variants.append(variant)
        
        return variants
    
    def _create_character_level_tokens(self, text: str) -> List[str]:
        """Create character-level tokens for Thai text."""
        tokens = []
        current_token = ""
        
        for char in text:
            if self._is_thai_char(char):
                current_token += char
                # Split on syllable boundaries (approximate)
                if len(current_token) >= 2:
                    tokens.append(current_token)
                    current_token = ""
            else:
                if current_token:
                    tokens.append(current_token)
                    current_token = ""
                if char.strip():
                    tokens.append(char)
        
        if current_token:
            tokens.append(current_token)
        
        return tokens
    
    def _optimize_variant_selection(
        self, 
        variants: List[QueryVariant], 
        query_analysis: Dict[str, Any]
    ) -> List[QueryVariant]:
        """Optimize variant selection and adjust weights based on analysis."""
        if not variants:
            return variants
        
        # Adjust weights based on query characteristics
        for variant in variants:
            # Boost weights for Thai content with Thai tokenization
            if (query_analysis["thai_content_detected"] and 
                variant.is_tokenized and 
                "thai" in variant.tokenization_engine.lower()):
                variant.weight = min(1.0, variant.weight * 1.1)
            
            # Reduce weights for fallback variants if good tokenization exists
            if variant.is_fallback and any(v.is_tokenized and v.weight > 0.8 for v in variants):
                variant.weight *= 0.8
            
            # Boost original query for short queries
            if variant.is_original and len(query_analysis.get("original_query", "")) < 10:
                variant.weight = min(1.0, variant.weight * 1.05)
        
        # Remove very low weight variants to improve performance
        min_weight_threshold = 0.2
        variants = [v for v in variants if v.weight >= min_weight_threshold]
        
        # Ensure we always have at least one variant
        if not variants and query_analysis.get("original_query"):
            # Create emergency fallback
            emergency_variant = QueryVariant(
                query_text=query_analysis["original_query"],
                variant_type=QueryVariantType.ORIGINAL,
                tokenization_engine="emergency",
                weight=0.5,
                search_options={"matching_strategy": "all"}
            )
            variants = [emergency_variant]
        
        return variants
    
    def _determine_variant_type(
        self, 
        result: TokenizationResult, 
        query_analysis: Dict[str, Any]
    ) -> QueryVariantType:
        """Determine the appropriate variant type based on tokenization result."""
        if "compound" in result.engine:
            return QueryVariantType.COMPOUND_SPLIT
        elif "fallback" in result.engine or "character" in result.engine:
            return QueryVariantType.FALLBACK
        elif query_analysis["mixed_content"]:
            return QueryVariantType.MIXED_LANGUAGE
        else:
            return QueryVariantType.TOKENIZED
    
    def _calculate_variant_weight(
        self, 
        variant_type: QueryVariantType, 
        query_analysis: Dict[str, Any],
        tokenization_confidence: float = 1.0
    ) -> float:
        """
        Calculate optimized weight for a query variant based on multiple factors.
        
        Args:
            variant_type: Type of query variant
            query_analysis: Query analysis results
            tokenization_confidence: Confidence from tokenization
            
        Returns:
            Weight value between 0.0 and 1.0
        """
        # Base weights by variant type
        base_weights = {
            QueryVariantType.ORIGINAL: 0.8,
            QueryVariantType.TOKENIZED: 1.0,
            QueryVariantType.COMPOUND_SPLIT: 0.9,
            QueryVariantType.FALLBACK: 0.6,
            QueryVariantType.MIXED_LANGUAGE: 0.85
        }
        
        base_weight = base_weights.get(variant_type, 0.5)
        
        # Factor 1: Content type adjustments
        content_multiplier = self._calculate_content_type_multiplier(
            variant_type, query_analysis
        )
        
        # Factor 2: Query length adjustments
        length_multiplier = self._calculate_length_multiplier(
            query_analysis.get("total_length", 0), variant_type
        )
        
        # Factor 3: Language confidence adjustments
        language_multiplier = self._calculate_language_confidence_multiplier(
            query_analysis, variant_type
        )
        
        # Factor 4: Tokenization quality adjustments
        tokenization_multiplier = self._calculate_tokenization_quality_multiplier(
            tokenization_confidence, variant_type
        )
        
        # Combine all factors
        final_weight = (
            base_weight * 
            content_multiplier * 
            length_multiplier * 
            language_multiplier * 
            tokenization_multiplier
        )
        
        # Apply bounds and return
        return max(0.1, min(1.0, final_weight))
    
    def _calculate_content_type_multiplier(
        self, 
        variant_type: QueryVariantType, 
        query_analysis: Dict[str, Any]
    ) -> float:
        """Calculate multiplier based on content type and variant compatibility."""
        thai_ratio = query_analysis.get("thai_content_ratio", 0.0)
        english_ratio = query_analysis.get("english_content_ratio", 0.0)
        mixed_content = query_analysis.get("mixed_content", False)
        
        # Thai content optimizations
        if thai_ratio > 0.7:  # Primarily Thai content
            if variant_type in [QueryVariantType.TOKENIZED, QueryVariantType.COMPOUND_SPLIT]:
                return 1.2  # Strong boost for Thai tokenization
            elif variant_type == QueryVariantType.ORIGINAL:
                return 0.9  # Slight reduction for original with Thai content
        
        # English content optimizations
        elif english_ratio > 0.7:  # Primarily English content
            if variant_type == QueryVariantType.ORIGINAL:
                return 1.1  # Boost original for English content
            elif variant_type in [QueryVariantType.TOKENIZED, QueryVariantType.COMPOUND_SPLIT]:
                return 0.8  # Reduce Thai tokenization for English content
        
        # Mixed content optimizations
        elif mixed_content:
            if variant_type == QueryVariantType.MIXED_LANGUAGE:
                return 1.15  # Boost mixed language variants
            elif variant_type == QueryVariantType.ORIGINAL:
                return 1.05  # Slight boost for original with mixed content
        
        return 1.0  # No adjustment
    
    def _calculate_length_multiplier(
        self, 
        query_length: int, 
        variant_type: QueryVariantType
    ) -> float:
        """Calculate multiplier based on query length."""
        if query_length <= 5:  # Very short queries
            if variant_type == QueryVariantType.ORIGINAL:
                return 1.1  # Boost original for short queries
            elif variant_type == QueryVariantType.FALLBACK:
                return 0.8  # Reduce fallback for short queries
        
        elif query_length >= 50:  # Long queries
            if variant_type in [QueryVariantType.TOKENIZED, QueryVariantType.COMPOUND_SPLIT]:
                return 1.1  # Boost tokenization for long queries
            elif variant_type == QueryVariantType.ORIGINAL:
                return 0.95  # Slight reduction for original with long queries
        
        return 1.0  # No adjustment for medium-length queries
    
    def _calculate_language_confidence_multiplier(
        self, 
        query_analysis: Dict[str, Any], 
        variant_type: QueryVariantType
    ) -> float:
        """Calculate multiplier based on language detection confidence."""
        primary_language = query_analysis.get("primary_language", "unknown")
        thai_ratio = query_analysis.get("thai_content_ratio", 0.0)
        
        # High confidence Thai detection
        if primary_language == "thai" and thai_ratio > 0.8:
            if variant_type in [QueryVariantType.TOKENIZED, QueryVariantType.COMPOUND_SPLIT]:
                return 1.1
            elif variant_type == QueryVariantType.FALLBACK:
                return 0.7
        
        # High confidence English detection
        elif primary_language == "english":
            if variant_type == QueryVariantType.ORIGINAL:
                return 1.05
            elif variant_type in [QueryVariantType.TOKENIZED, QueryVariantType.COMPOUND_SPLIT]:
                return 0.9
        
        # Low confidence or mixed language
        elif primary_language in ["mixed", "unknown"]:
            if variant_type == QueryVariantType.FALLBACK:
                return 1.1  # Boost fallback for uncertain language detection
        
        return 1.0
    
    def _calculate_tokenization_quality_multiplier(
        self, 
        tokenization_confidence: float, 
        variant_type: QueryVariantType
    ) -> float:
        """Calculate multiplier based on tokenization quality."""
        if variant_type == QueryVariantType.ORIGINAL:
            return 1.0  # Original doesn't depend on tokenization quality
        
        # High confidence tokenization
        if tokenization_confidence >= 0.9:
            return 1.1
        
        # Medium confidence tokenization
        elif tokenization_confidence >= 0.7:
            return 1.0
        
        # Low confidence tokenization
        elif tokenization_confidence >= 0.5:
            return 0.9
        
        # Very low confidence tokenization
        else:
            return 0.8
    
    def _get_search_options_for_variant(self, variant_type: QueryVariantType) -> Dict[str, Any]:
        """
        Get Meilisearch-specific search options for a variant type.
        
        Args:
            variant_type: Type of query variant
            
        Returns:
            Dictionary of search options
        """
        base_options = {
            "matching_strategy": "last",
            "showMatchesPosition": True
        }
        
        # Customize options based on variant type
        if variant_type == QueryVariantType.ORIGINAL:
            base_options["matching_strategy"] = "all"
        elif variant_type == QueryVariantType.TOKENIZED:
            base_options["matching_strategy"] = "last"
        elif variant_type == QueryVariantType.COMPOUND_SPLIT:
            base_options["matching_strategy"] = "last"
        elif variant_type == QueryVariantType.FALLBACK:
            base_options["matching_strategy"] = "all"
        elif variant_type == QueryVariantType.MIXED_LANGUAGE:
            base_options["matching_strategy"] = "last"
        
        return base_options
    
    async def _create_fallback_processed_query(
        self, 
        query: str, 
        processing_time: float
    ) -> ProcessedQuery:
        """
        Create a fallback ProcessedQuery when processing fails.
        
        Args:
            query: Original query text
            processing_time: Time spent on failed processing
            
        Returns:
            Minimal ProcessedQuery for fallback search
        """
        # Create minimal tokenization result
        fallback_tokenization = TokenizationResult(
            engine="fallback_error",
            tokens=[query],
            processing_time_ms=processing_time,
            confidence=0.1,
            success=False,
            error_message="Query processing failed"
        )
        
        # Create original query variant only
        fallback_variant = QueryVariant(
            query_text=query,
            variant_type=QueryVariantType.ORIGINAL,
            tokenization_engine="none",
            weight=0.5,
            search_options={"matching_strategy": "all"},
            metadata={"fallback_used": True}
        )
        
        return ProcessedQuery(
            original_query=query,
            tokenization_results=[fallback_tokenization],
            query_variants=[fallback_variant],
            processing_time_ms=processing_time,
            thai_content_detected=False,
            mixed_content=False,
            primary_language="unknown",
            fallback_used=True
        )
    
    def _is_thai_text(self, text: str) -> bool:
        """Check if text contains primarily Thai characters."""
        if not text:
            return False
        
        thai_chars = sum(1 for char in text if self._is_thai_char(char))
        return thai_chars / len(text) > 0.5
    
    def _is_thai_char(self, char: str) -> bool:
        """Check if character is Thai."""
        return self._thai_char_range[0] <= ord(char) <= self._thai_char_range[1]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query processor statistics and configuration."""
        return {
            "initialized": self._initialized,
            "primary_engine": self.settings.tokenization.primary_engine,
            "fallback_engines": list(self._fallback_segmenters.keys()),
            "settings": {
                "timeout_ms": self.settings.tokenization.timeout_ms,
                "confidence_threshold": self.settings.tokenization.confidence_threshold,
                "enable_compound_splitting": self.settings.tokenization.enable_compound_splitting,
                "preserve_original": self.settings.tokenization.preserve_original,
                "mixed_language_detection": self.settings.tokenization.mixed_language_detection,
                "max_query_variants": self.settings.search.max_query_variants
            }
        }