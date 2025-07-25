"""Tokenization endpoints for the Thai tokenizer API."""

import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse

from src.api.models.requests import TokenizeRequest, QueryProcessingRequest, SearchResultEnhancementRequest
from src.api.models.responses import TokenizationResult, ErrorResponse, QueryProcessingResult, SearchResultEnhancementResult
from src.tokenizer.thai_segmenter import ThaiSegmenter
from src.tokenizer.token_processor import TokenProcessor
from src.tokenizer.query_processor import QueryProcessor
from src.tokenizer.result_enhancer import SearchResultEnhancer
from src.utils.logging import get_structured_logger, set_correlation_id, generate_correlation_id

logger = get_structured_logger(__name__)

router = APIRouter()

# Global instances (will be injected via dependency injection)
_thai_segmenter: ThaiSegmenter = None
_token_processor: TokenProcessor = None
_query_processor: QueryProcessor = None
_result_enhancer: SearchResultEnhancer = None


def get_thai_segmenter() -> ThaiSegmenter:
    """Dependency to get Thai segmenter instance."""
    global _thai_segmenter
    if _thai_segmenter is None:
        _thai_segmenter = ThaiSegmenter()
    return _thai_segmenter


def get_token_processor() -> TokenProcessor:
    """Dependency to get token processor instance."""
    global _token_processor
    if _token_processor is None:
        _token_processor = TokenProcessor()
    return _token_processor


def get_query_processor() -> QueryProcessor:
    """Dependency to get query processor instance."""
    global _query_processor
    if _query_processor is None:
        _query_processor = QueryProcessor()
    return _query_processor


def get_result_enhancer() -> SearchResultEnhancer:
    """Dependency to get result enhancer instance."""
    global _result_enhancer
    if _result_enhancer is None:
        _result_enhancer = SearchResultEnhancer()
    return _result_enhancer


@router.post("/tokenize", response_model=TokenizationResult)
async def tokenize_text(
    request: TokenizeRequest,
    http_request: Request,
    thai_segmenter: ThaiSegmenter = Depends(get_thai_segmenter),
    token_processor: TokenProcessor = Depends(get_token_processor)
):
    """
    Tokenize Thai text into word segments.
    
    This endpoint segments Thai text using PyThaiNLP and returns the tokens
    along with word boundaries and processing metadata.
    """
    # Set correlation ID for request tracking
    correlation_id = http_request.headers.get("X-Correlation-ID", generate_correlation_id())
    set_correlation_id(correlation_id)
    
    try:
        logger.info("Tokenization request received", 
                   text_length=len(request.text),
                   include_confidence=request.include_confidence,
                   endpoint="tokenize")
        
        if not request.text.strip():
            return TokenizationResult(
                original_text=request.text,
                tokens=[],
                word_boundaries=[],
                confidence_scores=[] if request.include_confidence else None,
                processing_time_ms=0
            )
        
        # Perform tokenization
        tokenization_result = thai_segmenter.segment_text(request.text)
        
        # Process tokens for MeiliSearch compatibility
        token_result = token_processor.process_tokenization_result(tokenization_result)
        
        # Prepare confidence scores if requested
        confidence_scores = None
        if request.include_confidence:
            # For now, return uniform confidence scores
            # In a real implementation, this would come from the tokenizer
            confidence_scores = [0.95] * len(tokenization_result.tokens)
        
        response = TokenizationResult(
            original_text=tokenization_result.original_text,
            tokens=tokenization_result.tokens,
            word_boundaries=tokenization_result.word_boundaries,
            confidence_scores=confidence_scores,
            processing_time_ms=int(tokenization_result.processing_time_ms)
        )
        
        logger.info("Tokenization completed successfully",
                   token_count=len(response.tokens),
                   processing_time_ms=response.processing_time_ms,
                   endpoint="tokenize")
        
        return response
        
    except Exception as e:
        logger.error("Tokenization failed", error=e, 
                    text_length=len(request.text),
                    endpoint="tokenize")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="tokenization_error",
                message=f"Failed to tokenize text: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/tokenize/compound", response_model=TokenizationResult)
async def tokenize_compound_words(
    request: TokenizeRequest,
    thai_segmenter: ThaiSegmenter = Depends(get_thai_segmenter),
    token_processor: TokenProcessor = Depends(get_token_processor)
):
    """
    Specialized tokenization for Thai compound words.
    
    This endpoint uses enhanced processing to better handle compound words
    by trying multiple tokenization engines and strategies.
    """
    try:
        logger.info(f"Tokenizing compound words: {len(request.text)} characters")
        
        if not request.text.strip():
            return TokenizationResult(
                original_text=request.text,
                tokens=[],
                word_boundaries=[],
                confidence_scores=[] if request.include_confidence else None,
                processing_time_ms=0
            )
        
        # Perform compound word tokenization
        tokenization_result = thai_segmenter.segment_compound_words(request.text)
        
        # Process tokens for MeiliSearch compatibility
        token_result = token_processor.process_tokenization_result(tokenization_result)
        
        # Prepare confidence scores if requested
        confidence_scores = None
        if request.include_confidence:
            # For compound words, confidence might be lower
            confidence_scores = [0.85] * len(tokenization_result.tokens)
        
        response = TokenizationResult(
            original_text=tokenization_result.original_text,
            tokens=tokenization_result.tokens,
            word_boundaries=tokenization_result.word_boundaries,
            confidence_scores=confidence_scores,
            processing_time_ms=int(tokenization_result.processing_time_ms)
        )
        
        logger.info(
            f"Compound tokenization completed: {len(response.tokens)} tokens "
            f"in {response.processing_time_ms}ms"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Compound tokenization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="compound_tokenization_error",
                message=f"Failed to tokenize compound words: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/query/process", response_model=QueryProcessingResult)
async def process_search_query(
    request: QueryProcessingRequest,
    query_processor: QueryProcessor = Depends(get_query_processor)
):
    """
    Process Thai search query for optimal search results.
    
    This endpoint processes Thai search queries to handle partial compound words,
    generate search variants, and maintain search intent for better matching.
    """
    try:
        logger.info(f"Processing search query: '{request.query}'")
        
        if not request.query.strip():
            return QueryProcessingResult(
                original_query=request.query,
                processed_query=request.query,
                query_tokens=[],
                search_variants=[],
                suggested_completions=[],
                processing_metadata={"empty_query": True}
            )
        
        # Configure query processor based on request
        query_processor.enable_query_expansion = request.enable_query_expansion
        query_processor.enable_partial_matching = request.enable_partial_matching
        
        # Process the query
        result = query_processor.process_search_query(request.query)
        
        # Limit suggestions if requested
        suggestions = result.suggested_completions
        if not request.include_suggestions:
            suggestions = []
        elif len(suggestions) > request.max_suggestions:
            suggestions = suggestions[:request.max_suggestions]
        
        # Convert internal models to API models
        api_tokens = []
        for token in result.query_tokens:
            api_token = {
                "original": token.original,
                "processed": token.processed,
                "query_type": token.query_type.value,
                "is_partial": token.is_partial,
                "compound_parts": token.compound_parts,
                "search_variants": token.search_variants,
                "boost_score": token.boost_score
            }
            api_tokens.append(api_token)
        
        response = QueryProcessingResult(
            original_query=result.original_query,
            processed_query=result.processed_query,
            query_tokens=api_tokens,
            search_variants=result.search_variants,
            suggested_completions=suggestions,
            processing_metadata=result.processing_metadata
        )
        
        logger.info(
            f"Query processing completed: {len(api_tokens)} tokens, "
            f"{len(result.search_variants)} variants in "
            f"{result.processing_metadata.get('processing_time_ms', 0):.2f}ms"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="query_processing_error",
                message=f"Failed to process search query: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/query/compound", response_model=QueryProcessingResult)
async def process_compound_query(
    request: QueryProcessingRequest,
    query_processor: QueryProcessor = Depends(get_query_processor)
):
    """
    Specialized processing for partial compound word queries.
    
    This endpoint provides enhanced processing for Thai compound word queries,
    with better handling of partial matches and compound word variants.
    """
    try:
        logger.info(f"Processing compound query: '{request.query}'")
        
        if not request.query.strip():
            return QueryProcessingResult(
                original_query=request.query,
                processed_query=request.query,
                query_tokens=[],
                search_variants=[],
                suggested_completions=[],
                processing_metadata={"empty_query": True}
            )
        
        # Configure query processor
        query_processor.enable_query_expansion = request.enable_query_expansion
        query_processor.enable_partial_matching = request.enable_partial_matching
        
        # Process as compound query
        result = query_processor.process_partial_compound_query(request.query)
        
        # Limit suggestions if requested
        suggestions = result.suggested_completions
        if not request.include_suggestions:
            suggestions = []
        elif len(suggestions) > request.max_suggestions:
            suggestions = suggestions[:request.max_suggestions]
        
        # Convert internal models to API models
        api_tokens = []
        for token in result.query_tokens:
            api_token = {
                "original": token.original,
                "processed": token.processed,
                "query_type": token.query_type.value,
                "is_partial": token.is_partial,
                "compound_parts": token.compound_parts,
                "search_variants": token.search_variants,
                "boost_score": token.boost_score
            }
            api_tokens.append(api_token)
        
        response = QueryProcessingResult(
            original_query=result.original_query,
            processed_query=result.processed_query,
            query_tokens=api_tokens,
            search_variants=result.search_variants,
            suggested_completions=suggestions,
            processing_metadata=result.processing_metadata
        )
        
        logger.info(
            f"Compound query processing completed: {len(api_tokens)} tokens, "
            f"{len(result.search_variants)} variants"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Compound query processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="compound_query_processing_error",
                message=f"Failed to process compound query: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/search/enhance", response_model=SearchResultEnhancementResult)
async def enhance_search_results(
    request: SearchResultEnhancementRequest,
    result_enhancer: SearchResultEnhancer = Depends(get_result_enhancer)
):
    """
    Enhance search results with Thai-specific improvements.
    
    This endpoint post-processes search results to improve highlighting,
    relevance scoring, and result presentation for Thai compound words.
    """
    try:
        logger.info(f"Enhancing search results for query: '{request.original_query}'")
        
        # Configure enhancer based on request
        result_enhancer.enable_compound_highlighting = request.enable_compound_highlighting
        result_enhancer.enable_relevance_boosting = request.enable_relevance_boosting
        
        # Enhance the search results
        enhancement = result_enhancer.enhance_search_results(
            request.search_results,
            request.original_query,
            request.highlight_fields
        )
        
        # Convert internal models to API models
        api_hits = []
        for hit in enhancement.enhanced_hits:
            # Convert highlight spans
            api_spans = []
            for span in hit.highlight_spans:
                api_span = {
                    "start": span.start,
                    "end": span.end,
                    "text": span.text,
                    "highlight_type": span.highlight_type.value,
                    "confidence": span.confidence,
                    "matched_query": span.matched_query
                }
                api_spans.append(api_span)
            
            api_hit = {
                "original_hit": hit.original_hit,
                "enhanced_score": hit.enhanced_score,
                "highlight_spans": api_spans,
                "compound_matches": hit.compound_matches,
                "original_text_preserved": hit.original_text_preserved,
                "tokenized_text": hit.tokenized_text,
                "relevance_factors": hit.relevance_factors
            }
            api_hits.append(api_hit)
        
        response = SearchResultEnhancementResult(
            original_results=enhancement.original_results,
            enhanced_hits=api_hits,
            query_analysis=enhancement.query_analysis,
            enhancement_metadata=enhancement.enhancement_metadata
        )
        
        logger.info(
            f"Search result enhancement completed: {len(api_hits)} hits enhanced, "
            f"{enhancement.enhancement_metadata.get('compound_matches', 0)} compound matches found"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Search result enhancement failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="search_enhancement_error",
                message=f"Failed to enhance search results: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/tokenize/stats")
async def get_tokenization_stats(
    thai_segmenter: ThaiSegmenter = Depends(get_thai_segmenter),
    token_processor: TokenProcessor = Depends(get_token_processor),
    query_processor: QueryProcessor = Depends(get_query_processor),
    result_enhancer: SearchResultEnhancer = Depends(get_result_enhancer)
):
    """
    Get tokenization statistics and configuration.
    
    Returns information about the current tokenizer configuration,
    performance statistics, and available engines.
    """
    try:
        segmenter_stats = thai_segmenter.get_stats()
        processor_stats = token_processor.get_stats()
        query_stats = query_processor.get_stats()
        enhancer_stats = result_enhancer.get_stats()
        
        return {
            "tokenizer": {
                "engine": segmenter_stats.get("engine"),
                "custom_dict_size": segmenter_stats.get("custom_dict_size", 0),
                "keep_whitespace": segmenter_stats.get("keep_whitespace", True),
                "has_custom_tokenizer": segmenter_stats.get("has_custom_tokenizer", False)
            },
            "processor": {
                "separator_count": processor_stats.get("separator_count", 0),
                "preserve_original": processor_stats.get("preserve_original", True),
                "handle_compounds": processor_stats.get("handle_compounds", True)
            },
            "query_processor": {
                "query_expansion_enabled": query_stats.get("query_expansion_enabled", True),
                "partial_matching_enabled": query_stats.get("partial_matching_enabled", True),
                "compound_patterns_count": query_stats.get("compound_patterns_count", 0)
            },
            "result_enhancer": {
                "compound_highlighting_enabled": enhancer_stats.get("compound_highlighting_enabled", True),
                "relevance_boosting_enabled": enhancer_stats.get("relevance_boosting_enabled", True),
                "highlight_patterns_count": enhancer_stats.get("highlight_patterns_count", 0)
            },
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get tokenization stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="stats_error",
                message=f"Failed to retrieve tokenization statistics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )