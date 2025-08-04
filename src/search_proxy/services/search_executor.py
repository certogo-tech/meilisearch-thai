"""
Search execution engine for the Thai search proxy service.

This module provides the SearchExecutor class that performs parallel searches
against Meilisearch using different query variants, with proper error handling
and timeout management.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

from ...meilisearch_integration.client import MeiliSearchClient
from ...utils.logging import get_structured_logger
from ..models.query import QueryVariant
from ..models.search import SearchResult
from ..models.responses import SearchHit
from ..models.requests import SearchOptions


logger = get_structured_logger(__name__)


@dataclass
class SearchExecutorConfig:
    """Configuration for search execution."""
    max_concurrent_searches: int = 5
    search_timeout_ms: int = 10000
    enable_parallel_execution: bool = True
    retry_failed_searches: bool = True
    max_retries: int = 2
    retry_delay_ms: int = 100


class SearchExecutor:
    """
    Executes searches against Meilisearch with different query variants.
    
    Provides parallel search execution with proper error handling,
    timeout management, and result collection.
    """
    
    def __init__(
        self, 
        meilisearch_client: MeiliSearchClient,
        config: Optional[SearchExecutorConfig] = None
    ):
        """Initialize SearchExecutor with Meilisearch client and configuration."""
        self.client = meilisearch_client
        self.config = config or SearchExecutorConfig()
        self._search_semaphore = asyncio.Semaphore(self.config.max_concurrent_searches)
        
    async def execute_parallel_searches(
        self, 
        query_variants: List[QueryVariant], 
        index_name: str,
        search_options: Optional[SearchOptions] = None
    ) -> List[SearchResult]:
        """
        Execute searches in parallel for all query variants.
        
        Args:
            query_variants: List of query variants to search with
            index_name: Name of the Meilisearch index to search
            search_options: SearchOptions object with configuration
            
        Returns:
            List of SearchResult objects, one for each variant
        """
        if not query_variants:
            logger.warning("No query variants provided for search execution")
            return []
        
        start_time = time.time()
        
        logger.info(
            "Starting parallel search execution",
            extra={
                "variant_count": len(query_variants),
                "index_name": index_name,
                "max_concurrent": self.config.max_concurrent_searches,
                "parallel_enabled": self.config.enable_parallel_execution
            }
        )
        
        try:
            if self.config.enable_parallel_execution and len(query_variants) > 1:
                # Execute searches in parallel
                tasks = [
                    self._execute_single_search_with_semaphore(
                        variant, index_name, search_options
                    )
                    for variant in query_variants
                ]
                
                # Wait for all searches to complete with timeout
                timeout_seconds = self.config.search_timeout_ms / 1000
                search_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout_seconds
                )
                
                # Process results and handle exceptions
                results = []
                for i, result in enumerate(search_results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Search failed for variant {i}",
                            extra={
                                "variant_type": query_variants[i].variant_type.value,
                                "error": str(result)
                            }
                        )
                        # Create failed search result
                        results.append(self._create_failed_search_result(
                            query_variants[i], str(result)
                        ))
                    else:
                        results.append(result)
                        
            else:
                # Execute searches sequentially
                results = []
                for variant in query_variants:
                    result = await self._execute_single_search_with_semaphore(
                        variant, index_name, search_options
                    )
                    results.append(result)
            
            execution_time = (time.time() - start_time) * 1000
            successful_searches = sum(1 for r in results if r.success)
            
            logger.info(
                "Parallel search execution completed",
                extra={
                    "total_variants": len(query_variants),
                    "successful_searches": successful_searches,
                    "failed_searches": len(results) - successful_searches,
                    "execution_time_ms": execution_time,
                    "index_name": index_name
                }
            )
            
            return results
            
        except asyncio.TimeoutError:
            logger.error(
                "Search execution timed out",
                extra={
                    "timeout_ms": self.config.search_timeout_ms,
                    "variant_count": len(query_variants),
                    "index_name": index_name
                }
            )
            # Return failed results for all variants
            return [
                self._create_failed_search_result(variant, "Search execution timed out")
                for variant in query_variants
            ]
            
        except Exception as e:
            logger.error(
                "Unexpected error during parallel search execution",
                extra={
                    "error": str(e),
                    "variant_count": len(query_variants),
                    "index_name": index_name
                }
            )
            # Return failed results for all variants
            return [
                self._create_failed_search_result(variant, f"Execution error: {str(e)}")
                for variant in query_variants
            ]
    
    async def execute_single_search(
        self, 
        variant: QueryVariant, 
        index_name: str,
        search_options: Optional[SearchOptions] = None
    ) -> SearchResult:
        """
        Execute a single search for a query variant.
        
        Args:
            variant: Query variant to search with
            index_name: Name of the Meilisearch index to search
            search_options: SearchOptions object with configuration
            
        Returns:
            SearchResult object with search results or error information
        """
        start_time = time.time()
        
        # Create variant-specific Meilisearch parameters
        if search_options:
            meilisearch_params = self.translate_search_options_to_meilisearch(search_options, variant)
        else:
            # Use default options if none provided
            default_options = SearchOptions()
            meilisearch_params = self.translate_search_options_to_meilisearch(default_options, variant)
        
        logger.debug(
            "Executing single search",
            extra={
                "query_text": variant.query_text[:100],  # Truncate for logging
                "variant_type": variant.variant_type.value,
                "tokenization_engine": variant.tokenization_engine,
                "weight": variant.weight,
                "index_name": index_name,
                "meilisearch_params": meilisearch_params
            }
        )
        
        try:
            # Execute search with retry logic if enabled
            if self.config.retry_failed_searches:
                raw_results = await self._search_with_retry(
                    index_name, variant.query_text, meilisearch_params
                )
            else:
                raw_results = await self.client.search(
                    index_name, variant.query_text, meilisearch_params
                )
            
            processing_time = (time.time() - start_time) * 1000
            
            # Convert raw results to SearchHit objects
            hits = self._convert_raw_hits_to_search_hits(
                raw_results.get('hits', []), variant
            )
            
            # Extract metadata from Meilisearch response
            meilisearch_metadata = {
                'query': raw_results.get('query', ''),
                'processingTimeMs': raw_results.get('processingTimeMs', 0),
                'limit': raw_results.get('limit', 0),
                'offset': raw_results.get('offset', 0),
                'estimatedTotalHits': raw_results.get('estimatedTotalHits', 0)
            }
            
            search_result = SearchResult(
                query_variant=variant,
                hits=hits,
                total_hits=raw_results.get('estimatedTotalHits', len(hits)),
                processing_time_ms=processing_time,
                success=True,
                error_message=None,
                meilisearch_metadata=meilisearch_metadata
            )
            
            logger.debug(
                "Single search completed successfully",
                extra={
                    "variant_type": variant.variant_type.value,
                    "hits_count": len(hits),
                    "total_hits": search_result.total_hits,
                    "processing_time_ms": processing_time,
                    "index_name": index_name
                }
            )
            
            return search_result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_message = f"Search failed: {str(e)}"
            
            logger.error(
                "Single search failed",
                extra={
                    "variant_type": variant.variant_type.value,
                    "error": error_message,
                    "processing_time_ms": processing_time,
                    "index_name": index_name,
                    "query_text": variant.query_text[:100]
                }
            )
            
            return SearchResult(
                query_variant=variant,
                hits=[],
                total_hits=0,
                processing_time_ms=processing_time,
                success=False,
                error_message=error_message,
                meilisearch_metadata={}
            )
    
    async def _execute_single_search_with_semaphore(
        self, 
        variant: QueryVariant, 
        index_name: str,
        search_options: Optional[SearchOptions]
    ) -> SearchResult:
        """Execute single search with semaphore for concurrency control."""
        async with self._search_semaphore:
            return await self.execute_single_search(variant, index_name, search_options)
    
    async def _search_with_retry(
        self, 
        index_name: str, 
        query: str, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute search with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await self.client.search(index_name, query, options)
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    retry_delay = self.config.retry_delay_ms / 1000
                    logger.warning(
                        f"Search attempt {attempt + 1} failed, retrying in {retry_delay}s",
                        extra={
                            "error": str(e),
                            "attempt": attempt + 1,
                            "max_retries": self.config.max_retries,
                            "query": query[:100],
                            "index_name": index_name
                        }
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        f"Search failed after {self.config.max_retries + 1} attempts",
                        extra={
                            "error": str(e),
                            "query": query[:100],
                            "index_name": index_name
                        }
                    )
        
        raise last_exception
    
    def _convert_raw_hits_to_search_hits(
        self, 
        raw_hits: List[Dict[str, Any]], 
        variant: QueryVariant
    ) -> List[SearchHit]:
        """Convert raw Meilisearch hits to SearchHit objects."""
        search_hits = []
        
        # Log first hit to debug field names
        if raw_hits:
            logger.debug(
                "Raw hit structure",
                extra={
                    "hit_keys": list(raw_hits[0].keys()),
                    "sample_hit": {k: v for k, v in raw_hits[0].items() if k.startswith('_')}
                }
            )
        
        for hit in raw_hits:
            try:
                # Extract document data (remove Meilisearch metadata)
                document = {k: v for k, v in hit.items() if not k.startswith('_')}
                
                # MeiliSearch uses _score in some versions and _rankingScore in others
                score = float(hit.get('_rankingScore', hit.get('_score', 0.0)))
                
                search_hit = SearchHit(
                    id=str(hit.get('id', hit.get('_id', ''))),
                    score=score,
                    document=document,
                    highlight=hit.get('_formatted', {}),
                    ranking_info={
                        'base_score': score,
                        'variant_weight': variant.weight,
                        'variant_type': variant.variant_type.value,
                        'tokenization_engine': variant.tokenization_engine
                    }
                )
                search_hits.append(search_hit)
                
            except Exception as e:
                logger.warning(
                    "Failed to convert raw hit to SearchHit",
                    extra={
                        "error": str(e),
                        "hit_keys": list(hit.keys()) if isinstance(hit, dict) else "not_dict",
                        "variant_type": variant.variant_type.value
                    }
                )
                continue
        
        return search_hits
    
    def _create_failed_search_result(
        self, 
        variant: QueryVariant, 
        error_message: str
    ) -> SearchResult:
        """Create a SearchResult object for a failed search."""
        return SearchResult(
            query_variant=variant,
            hits=[],
            total_hits=0,
            processing_time_ms=0.0,
            success=False,
            error_message=error_message,
            meilisearch_metadata={}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the search executor and its dependencies."""
        try:
            # Check Meilisearch client health
            client_health = await self.client.health_check()
            
            return {
                "status": "healthy" if client_health["status"] == "healthy" else "unhealthy",
                "meilisearch_client": client_health,
                "config": {
                    "max_concurrent_searches": self.config.max_concurrent_searches,
                    "search_timeout_ms": self.config.search_timeout_ms,
                    "parallel_execution_enabled": self.config.enable_parallel_execution,
                    "retry_enabled": self.config.retry_failed_searches,
                    "max_retries": self.config.max_retries
                },
                "semaphore_available": self._search_semaphore._value
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "meilisearch_client": {"status": "unknown"}
            }
    
    def collect_and_deduplicate_results(
        self, 
        search_results: List[SearchResult],
        deduplication_strategy: str = "id_based"
    ) -> Tuple[List[SearchHit], Dict[str, Any]]:
        """
        Collect and deduplicate search results from multiple search variants.
        
        Args:
            search_results: List of SearchResult objects from different variants
            deduplication_strategy: Strategy for deduplication ("id_based", "content_based", "hybrid")
            
        Returns:
            Tuple of (deduplicated_hits, metadata)
        """
        start_time = time.time()
        
        if not search_results:
            return [], {"deduplication_count": 0, "processing_time_ms": 0.0}
        
        # Filter successful search results
        successful_results = [r for r in search_results if r.success]
        
        if not successful_results:
            logger.warning("No successful search results to collect and deduplicate")
            return [], {
                "deduplication_count": 0,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "successful_searches": 0,
                "failed_searches": len(search_results)
            }
        
        # Collect all hits with metadata
        all_hits_with_metadata = []
        for result in successful_results:
            for hit in result.hits:
                # Add search metadata to each hit
                hit_with_metadata = {
                    "hit": hit,
                    "variant_type": result.query_variant.variant_type.value,
                    "variant_weight": result.query_variant.weight,
                    "tokenization_engine": result.query_variant.tokenization_engine,
                    "search_processing_time": result.processing_time_ms
                }
                all_hits_with_metadata.append(hit_with_metadata)
        
        # Perform deduplication based on strategy
        if deduplication_strategy == "id_based":
            deduplicated_hits, dedup_count = self._deduplicate_by_id(all_hits_with_metadata)
        elif deduplication_strategy == "content_based":
            deduplicated_hits, dedup_count = self._deduplicate_by_content(all_hits_with_metadata)
        elif deduplication_strategy == "hybrid":
            deduplicated_hits, dedup_count = self._deduplicate_hybrid(all_hits_with_metadata)
        else:
            logger.warning(f"Unknown deduplication strategy: {deduplication_strategy}, using id_based")
            deduplicated_hits, dedup_count = self._deduplicate_by_id(all_hits_with_metadata)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Create metadata about the collection and deduplication process
        metadata = {
            "total_raw_hits": len(all_hits_with_metadata),
            "deduplicated_hits": len(deduplicated_hits),
            "deduplication_count": dedup_count,
            "deduplication_strategy": deduplication_strategy,
            "processing_time_ms": processing_time,
            "successful_searches": len(successful_results),
            "failed_searches": len(search_results) - len(successful_results),
            "variant_distribution": self._get_variant_distribution(successful_results),
            "engine_distribution": self._get_engine_distribution(successful_results)
        }
        
        logger.info(
            "Result collection and deduplication completed",
            extra={
                "total_raw_hits": metadata["total_raw_hits"],
                "deduplicated_hits": metadata["deduplicated_hits"],
                "deduplication_count": dedup_count,
                "strategy": deduplication_strategy,
                "processing_time_ms": processing_time
            }
        )
        
        return deduplicated_hits, metadata
    
    def _deduplicate_by_id(
        self, 
        hits_with_metadata: List[Dict[str, Any]]
    ) -> Tuple[List[SearchHit], int]:
        """Deduplicate hits based on document ID, keeping the highest scoring version."""
        seen_ids: Dict[str, Dict[str, Any]] = {}
        dedup_count = 0
        
        for item in hits_with_metadata:
            hit = item["hit"]
            doc_id = hit.id
            
            if doc_id in seen_ids:
                dedup_count += 1
                # Keep the hit with higher score, or higher variant weight if scores are equal
                existing_hit = seen_ids[doc_id]["hit"]
                if (hit.score > existing_hit.score or 
                    (hit.score == existing_hit.score and item["variant_weight"] > seen_ids[doc_id]["variant_weight"])):
                    seen_ids[doc_id] = item
            else:
                seen_ids[doc_id] = item
        
        # Extract the deduplicated hits
        deduplicated_hits = [item["hit"] for item in seen_ids.values()]
        
        return deduplicated_hits, dedup_count
    
    def _deduplicate_by_content(
        self, 
        hits_with_metadata: List[Dict[str, Any]]
    ) -> Tuple[List[SearchHit], int]:
        """Deduplicate hits based on content similarity."""
        # For content-based deduplication, we'll use a simple approach
        # comparing title and content fields
        seen_content: Dict[str, Dict[str, Any]] = {}
        dedup_count = 0
        
        for item in hits_with_metadata:
            hit = item["hit"]
            
            # Create a content signature
            title = hit.document.get("title", "")
            content = hit.document.get("content", "")
            content_signature = f"{title[:100]}|{content[:200]}"  # Use first 100/200 chars
            
            if content_signature in seen_content:
                dedup_count += 1
                # Keep the hit with higher score
                existing_hit = seen_content[content_signature]["hit"]
                if hit.score > existing_hit.score:
                    seen_content[content_signature] = item
            else:
                seen_content[content_signature] = item
        
        deduplicated_hits = [item["hit"] for item in seen_content.values()]
        
        return deduplicated_hits, dedup_count
    
    def _deduplicate_hybrid(
        self, 
        hits_with_metadata: List[Dict[str, Any]]
    ) -> Tuple[List[SearchHit], int]:
        """Hybrid deduplication using both ID and content similarity."""
        # First deduplicate by ID
        id_deduplicated, id_dedup_count = self._deduplicate_by_id(hits_with_metadata)
        
        # Then deduplicate by content on the remaining hits
        id_deduplicated_with_metadata = [
            {"hit": hit, "variant_weight": 1.0}  # Simplified metadata for second pass
            for hit in id_deduplicated
        ]
        
        final_deduplicated, content_dedup_count = self._deduplicate_by_content(
            id_deduplicated_with_metadata
        )
        
        total_dedup_count = id_dedup_count + content_dedup_count
        
        return final_deduplicated, total_dedup_count
    
    def _get_variant_distribution(self, search_results: List[SearchResult]) -> Dict[str, int]:
        """Get distribution of hits by variant type."""
        distribution = defaultdict(int)
        for result in search_results:
            distribution[result.query_variant.variant_type.value] += len(result.hits)
        return dict(distribution)
    
    def _get_engine_distribution(self, search_results: List[SearchResult]) -> Dict[str, int]:
        """Get distribution of hits by tokenization engine."""
        distribution = defaultdict(int)
        for result in search_results:
            distribution[result.query_variant.tokenization_engine] += len(result.hits)
        return dict(distribution)
    
    def add_search_metadata_to_hits(
        self, 
        hits: List[SearchHit], 
        search_results: List[SearchResult]
    ) -> List[SearchHit]:
        """
        Add search execution metadata to hits for debugging and analytics.
        
        Args:
            hits: List of deduplicated search hits
            search_results: Original search results for metadata extraction
            
        Returns:
            List of hits with enhanced metadata
        """
        # Create a mapping of hit IDs to search metadata
        hit_metadata_map = {}
        
        for result in search_results:
            if not result.success:
                continue
                
            for hit in result.hits:
                if hit.id not in hit_metadata_map:
                    hit_metadata_map[hit.id] = []
                
                hit_metadata_map[hit.id].append({
                    "variant_type": result.query_variant.variant_type.value,
                    "variant_weight": result.query_variant.weight,
                    "tokenization_engine": result.query_variant.tokenization_engine,
                    "search_processing_time": result.processing_time_ms,
                    "original_score": hit.score
                })
        
        # Enhance hits with metadata
        enhanced_hits = []
        for hit in hits:
            if hit.id in hit_metadata_map:
                # Add search execution metadata
                search_metadata = hit_metadata_map[hit.id]
                
                # Update ranking_info with search metadata
                if hit.ranking_info is None:
                    hit.ranking_info = {}
                
                hit.ranking_info.update({
                    "search_variants_matched": len(search_metadata),
                    "variant_types": [m["variant_type"] for m in search_metadata],
                    "tokenization_engines": [m["tokenization_engine"] for m in search_metadata],
                    "max_variant_weight": max(m["variant_weight"] for m in search_metadata),
                    "avg_processing_time": sum(m["search_processing_time"] for m in search_metadata) / len(search_metadata)
                })
            
            enhanced_hits.append(hit)
        
        return enhanced_hits
    
    def translate_search_options_to_meilisearch(
        self, 
        search_options: SearchOptions,
        variant: Optional[QueryVariant] = None
    ) -> Dict[str, Any]:
        """
        Translate SearchOptions to Meilisearch-specific search parameters.
        
        Args:
            search_options: SearchOptions object with configuration
            variant: Optional QueryVariant for variant-specific adjustments
            
        Returns:
            Dictionary of Meilisearch search parameters
        """
        meilisearch_params = {}
        
        # Basic pagination parameters
        meilisearch_params["limit"] = search_options.limit
        meilisearch_params["offset"] = search_options.offset
        
        # Filtering
        if search_options.filters:
            meilisearch_params["filter"] = self._format_filters_for_meilisearch(
                search_options.filters
            )
        
        # Sorting
        if search_options.sort:
            meilisearch_params["sort"] = search_options.sort
        
        # Highlighting configuration
        if search_options.highlight:
            highlight_config = {}
            
            if search_options.attributes_to_highlight:
                highlight_config["attributesToHighlight"] = search_options.attributes_to_highlight
            
            if search_options.crop_length:
                highlight_config["cropLength"] = search_options.crop_length
            
            if search_options.crop_marker:
                highlight_config["cropMarker"] = search_options.crop_marker
            
            # Add highlight config to params
            meilisearch_params.update(highlight_config)
        
        # Attributes to retrieve
        if search_options.attributes_to_retrieve:
            meilisearch_params["attributesToRetrieve"] = search_options.attributes_to_retrieve
        
        # Matching strategy
        meilisearch_params["matchingStrategy"] = search_options.matching_strategy
        
        # Always request ranking score
        meilisearch_params["showRankingScore"] = True
        
        # Variant-specific adjustments
        if variant:
            # Adjust matching strategy based on variant type
            if variant.variant_type.value == "original":
                # For original queries, use more strict matching
                meilisearch_params["matchingStrategy"] = "all"
            elif variant.variant_type.value in ["tokenized", "compound_split"]:
                # For tokenized queries, use more flexible matching
                meilisearch_params["matchingStrategy"] = "last"
            elif variant.variant_type.value == "fallback":
                # For fallback queries, use most flexible matching
                meilisearch_params["matchingStrategy"] = "frequency"
            
            # Merge variant-specific search options
            if variant.search_options:
                # Convert snake_case to camelCase for MeiliSearch
                for key, value in variant.search_options.items():
                    if key == "matching_strategy":
                        meilisearch_params["matchingStrategy"] = value
                    elif key == "show_matches_position":
                        meilisearch_params["showMatchesPosition"] = value
                    else:
                        meilisearch_params[key] = value
        
        logger.debug(
            "Translated search options to Meilisearch parameters",
            extra={
                "original_options": search_options.model_dump(),
                "meilisearch_params": meilisearch_params,
                "variant_type": variant.variant_type.value if variant else None
            }
        )
        
        return meilisearch_params
    
    def _format_filters_for_meilisearch(self, filters: Dict[str, Any]) -> str:
        """
        Format filters dictionary into Meilisearch filter string format.
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            Formatted filter string for Meilisearch
        """
        if not filters:
            return ""
        
        filter_parts = []
        
        for field, condition in filters.items():
            if isinstance(condition, dict):
                # Handle complex conditions like {"$gte": 100, "$lte": 200}
                for operator, value in condition.items():
                    if operator == "$eq":
                        filter_parts.append(f"{field} = {self._format_filter_value(value)}")
                    elif operator == "$ne":
                        filter_parts.append(f"{field} != {self._format_filter_value(value)}")
                    elif operator == "$gt":
                        filter_parts.append(f"{field} > {self._format_filter_value(value)}")
                    elif operator == "$gte":
                        filter_parts.append(f"{field} >= {self._format_filter_value(value)}")
                    elif operator == "$lt":
                        filter_parts.append(f"{field} < {self._format_filter_value(value)}")
                    elif operator == "$lte":
                        filter_parts.append(f"{field} <= {self._format_filter_value(value)}")
                    elif operator == "$in":
                        if isinstance(value, list):
                            in_values = " OR ".join([
                                f"{field} = {self._format_filter_value(v)}" for v in value
                            ])
                            filter_parts.append(f"({in_values})")
                    elif operator == "$exists":
                        if value:
                            filter_parts.append(f"{field} EXISTS")
                        else:
                            filter_parts.append(f"{field} NOT EXISTS")
            elif isinstance(condition, list):
                # Handle array conditions as IN operations
                in_values = " OR ".join([
                    f"{field} = {self._format_filter_value(v)}" for v in condition
                ])
                filter_parts.append(f"({in_values})")
            else:
                # Simple equality condition
                filter_parts.append(f"{field} = {self._format_filter_value(condition)}")
        
        # Join all filter parts with AND
        filter_string = " AND ".join(filter_parts)
        
        logger.debug(
            "Formatted filters for Meilisearch",
            extra={
                "original_filters": filters,
                "formatted_filter": filter_string
            }
        )
        
        return filter_string
    
    def _format_filter_value(self, value: Any) -> str:
        """Format a filter value for Meilisearch filter string."""
        if isinstance(value, str):
            # Escape quotes and wrap in quotes
            escaped_value = value.replace('"', '\\"')
            return f'"{escaped_value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif value is None:
            return "null"
        else:
            # Numbers and other types
            return str(value)
    
    def create_variant_specific_options(
        self, 
        base_options: SearchOptions,
        variant: QueryVariant
    ) -> Dict[str, Any]:
        """
        Create variant-specific search options by combining base options with variant settings.
        
        Args:
            base_options: Base SearchOptions from the request
            variant: QueryVariant with specific settings
            
        Returns:
            Combined search options for this variant
        """
        # Start with base Meilisearch parameters
        meilisearch_params = self.translate_search_options_to_meilisearch(
            base_options, variant
        )
        
        # Apply variant-specific optimizations
        if variant.variant_type.value == "original":
            # For original queries, prioritize exact matches
            meilisearch_params["matchingStrategy"] = "all"
            
        elif variant.variant_type.value in ["tokenized", "compound_split"]:
            # For tokenized queries, allow more flexible matching
            meilisearch_params["matchingStrategy"] = "last"
            
            # Adjust crop length for better Thai text display
            if "cropLength" in meilisearch_params:
                # Thai text may need more characters for meaningful context
                meilisearch_params["cropLength"] = min(
                    meilisearch_params["cropLength"] * 2, 400
                )
                
        elif variant.variant_type.value == "fallback":
            # For fallback queries, use most permissive settings
            meilisearch_params["matchingStrategy"] = "frequency"
            
            # Increase result limit for fallback to get more candidates
            meilisearch_params["limit"] = min(meilisearch_params["limit"] * 2, 100)
            
        elif variant.variant_type.value == "mixed_language":
            # For mixed language queries, optimize for both Thai and English
            meilisearch_params["matchingStrategy"] = "last"
            
            # Ensure both Thai and English attributes are highlighted
            if "attributesToHighlight" not in meilisearch_params:
                meilisearch_params["attributesToHighlight"] = ["*"]
        
        # Merge any variant-specific options
        if variant.search_options:
            meilisearch_params.update(variant.search_options)
        
        logger.debug(
            "Created variant-specific search options",
            extra={
                "variant_type": variant.variant_type.value,
                "tokenization_engine": variant.tokenization_engine,
                "variant_weight": variant.weight,
                "final_options": meilisearch_params
            }
        )
        
        return meilisearch_params
    
    def validate_search_options(self, options: SearchOptions) -> List[str]:
        """
        Validate search options and return list of validation errors.
        
        Args:
            options: SearchOptions to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate limit and offset
        if options.limit < 1 or options.limit > 100:
            errors.append("Limit must be between 1 and 100")
        
        if options.offset < 0:
            errors.append("Offset must be non-negative")
        
        # Validate crop length
        if options.crop_length < 10 or options.crop_length > 1000:
            errors.append("Crop length must be between 10 and 1000")
        
        # Validate matching strategy
        valid_strategies = ["all", "last", "frequency"]
        if options.matching_strategy not in valid_strategies:
            errors.append(f"Matching strategy must be one of: {valid_strategies}")
        
        # Validate sort fields format
        if options.sort:
            for sort_field in options.sort:
                if not isinstance(sort_field, str):
                    errors.append("Sort fields must be strings")
                    continue
                
                # Check for valid sort format (field:asc or field:desc)
                if ":" in sort_field:
                    field, direction = sort_field.split(":", 1)
                    if direction not in ["asc", "desc"]:
                        errors.append(f"Invalid sort direction '{direction}' for field '{field}'")
        
        # Validate filters structure
        if options.filters:
            filter_errors = self._validate_filters(options.filters)
            errors.extend(filter_errors)
        
        return errors
    
    def _validate_filters(self, filters: Dict[str, Any]) -> List[str]:
        """Validate filter structure and return errors."""
        errors = []
        
        for field, condition in filters.items():
            if not isinstance(field, str) or not field.strip():
                errors.append("Filter field names must be non-empty strings")
                continue
            
            if isinstance(condition, dict):
                # Validate operator conditions
                valid_operators = ["$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$exists"]
                for operator in condition.keys():
                    if operator not in valid_operators:
                        errors.append(f"Invalid filter operator '{operator}' for field '{field}'")
            
            elif isinstance(condition, list):
                # Validate array conditions
                if not condition:
                    errors.append(f"Filter array for field '{field}' cannot be empty")
            
            # Other types (string, number, boolean) are valid as-is
        
        return errors
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics and statistics."""
        return {
            "config": {
                "max_concurrent_searches": self.config.max_concurrent_searches,
                "search_timeout_ms": self.config.search_timeout_ms,
                "parallel_execution_enabled": self.config.enable_parallel_execution,
                "retry_enabled": self.config.retry_failed_searches,
                "max_retries": self.config.max_retries,
                "retry_delay_ms": self.config.retry_delay_ms
            },
            "runtime": {
                "semaphore_available": self._search_semaphore._value,
                "semaphore_locked": self.config.max_concurrent_searches - self._search_semaphore._value
            }
        }