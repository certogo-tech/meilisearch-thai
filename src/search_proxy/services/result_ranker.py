"""
Result ranking and scoring system for the Thai search proxy service.

This module provides the ResultRanker class that intelligently ranks and scores
search results from multiple query variants, considering Thai language-specific
factors and tokenization quality.
"""

import time
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import math
import hashlib
from difflib import SequenceMatcher

from ...utils.logging import get_structured_logger
from ..models.search import SearchResult, QueryContext, RankingMetadata, RankedResults
from ..models.responses import SearchHit
from ..models.query import QueryVariant, QueryVariantType
from ..config.settings import RankingConfig


logger = get_structured_logger(__name__)


class RankingAlgorithm(str, Enum):
    """Available ranking algorithms."""
    
    WEIGHTED_SCORE = "weighted_score"
    OPTIMIZED_SCORE = "optimized_score"
    SIMPLE_SCORE = "simple_score"
    EXPERIMENTAL_SCORE = "experimental_score"


# Additional ranking configuration not in settings
class ExtendedRankingConfig:
    """Extended configuration for result ranking beyond basic settings."""
    def __init__(self, base_config: RankingConfig):
        self.base_config = base_config
        self.position_decay_enabled: bool = True
        self.variant_weight_factor: float = 1.0
        self.tokenization_confidence_factor: float = 0.5
        
        # A/B testing configuration
        self.ab_testing_enabled: bool = False
        self.ab_test_algorithm: Optional[str] = None
        self.ab_test_traffic_percentage: float = 0.0
        self.ab_test_session_id: Optional[str] = None
        
        # Content type specific configurations
        self.content_type_configs: Dict[str, Dict[str, float]] = {
            "formal": {
                "boost_exact_matches": 2.2,
                "boost_thai_matches": 1.6,
                "boost_compound_matches": 1.4
            },
            "informal": {
                "boost_exact_matches": 1.8,
                "boost_thai_matches": 1.4,
                "boost_compound_matches": 1.2
            },
            "mixed": {
                "boost_exact_matches": 2.0,
                "boost_thai_matches": 1.3,
                "boost_compound_matches": 1.1
            }
        }
        
        # Performance tuning parameters
        self.similarity_threshold: float = 0.85
        self.max_similarity_comparisons: int = 100
        self.enable_content_similarity_deduplication: bool = True
        self.enable_performance_optimization: bool = True
        
        # Map algorithm string to enum
        algorithm_map = {
            "weighted_score": RankingAlgorithm.WEIGHTED_SCORE,
            "optimized_score": RankingAlgorithm.OPTIMIZED_SCORE,
            "simple_score": RankingAlgorithm.SIMPLE_SCORE,
            "experimental_score": RankingAlgorithm.EXPERIMENTAL_SCORE
        }
        self.algorithm = algorithm_map.get(base_config.algorithm, RankingAlgorithm.WEIGHTED_SCORE)
    
    @property
    def boost_exact_matches(self) -> float:
        return self.base_config.boost_exact_matches
    
    @property
    def boost_thai_matches(self) -> float:
        return self.base_config.boost_thai_matches
    
    @property
    def boost_compound_matches(self) -> float:
        return self.base_config.boost_compound_matches
    
    @property
    def decay_factor(self) -> float:
        return self.base_config.decay_factor
    
    @property
    def min_score_threshold(self) -> float:
        return self.base_config.min_score_threshold
    
    @property
    def max_results_per_variant(self) -> int:
        return self.base_config.max_results_per_variant
    
    @property
    def enable_score_normalization(self) -> bool:
        return self.base_config.enable_score_normalization


class ResultRanker:
    """
    Ranks and scores search results from multiple query variants.
    
    Provides configurable scoring algorithms that consider Thai language-specific
    factors, tokenization quality, and query variant characteristics.
    """
    
    def __init__(self, config: Optional[RankingConfig] = None):
        """Initialize ResultRanker with configuration."""
        base_config = config or RankingConfig()
        self.config = ExtendedRankingConfig(base_config)
        
        # Algorithm mapping
        self._algorithm_map = {
            RankingAlgorithm.WEIGHTED_SCORE: self._weighted_score_algorithm,
            RankingAlgorithm.OPTIMIZED_SCORE: self._optimized_score_algorithm,
            RankingAlgorithm.SIMPLE_SCORE: self._simple_score_algorithm,
            RankingAlgorithm.EXPERIMENTAL_SCORE: self._experimental_score_algorithm
        }
        
        # Performance metrics tracking
        self._performance_metrics = {
            "total_rankings": 0,
            "total_ranking_time_ms": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in RankingAlgorithm},
            "deduplication_stats": {
                "id_based": 0,
                "content_similarity": 0,
                "total_duplicates_removed": 0
            },
            "ab_test_stats": {
                "total_tests": 0,
                "algorithm_performance": {}
            }
        }
        
        logger.info(
            "ResultRanker initialized",
            extra={
                "algorithm": self.config.algorithm.value,
                "boost_exact_matches": self._get_boost_exact_matches(),
                "boost_thai_matches": self._get_boost_thai_matches(),
                "boost_compound_matches": self._get_boost_compound_matches(),
                "score_normalization": self.config.enable_score_normalization,
                "ab_testing_enabled": self.config.ab_testing_enabled,
                "content_type_configs": len(self.config.content_type_configs)
            }
        )
    
    def rank_results(
        self, 
        search_results: List[SearchResult], 
        original_query: str,
        query_context: Optional[QueryContext] = None,
        session_id: Optional[str] = None
    ) -> RankedResults:
        """
        Rank and merge search results from multiple query variants.
        
        Args:
            search_results: List of SearchResult objects from different variants
            original_query: Original search query for context
            query_context: Optional query processing context
            session_id: Optional session ID for A/B testing
            
        Returns:
            RankedResults object with ranked and merged results
        """
        start_time = time.time()
        
        if not search_results:
            logger.warning("No search results provided for ranking")
            return self._create_empty_ranked_results(original_query, query_context)
        
        # Filter successful search results
        successful_results = [r for r in search_results if r.success]
        
        if not successful_results:
            logger.warning("No successful search results to rank")
            return self._create_empty_ranked_results(original_query, query_context)
        
        # Create query context if not provided
        if query_context is None:
            query_context = self._create_query_context(original_query, successful_results)
        
        # Determine algorithm to use (with A/B testing support)
        algorithm_to_use = self._select_ranking_algorithm(query_context, session_id)
        
        logger.info(
            "Starting result ranking",
            extra={
                "total_results": len(search_results),
                "successful_results": len(successful_results),
                "algorithm": algorithm_to_use.value,
                "original_query_length": len(original_query),
                "ab_testing_active": self.config.ab_testing_enabled,
                "session_id": session_id
            }
        )
        
        # Apply content type specific configuration
        self._apply_content_type_configuration(query_context)
        
        # Collect and score all hits
        scored_hits = self._collect_and_score_hits(successful_results, query_context)
        
        # Apply ranking algorithm
        ranking_algorithm = self._algorithm_map.get(
            algorithm_to_use, 
            self._weighted_score_algorithm
        )
        
        ranked_hits = ranking_algorithm(scored_hits, query_context)
        
        # Apply score normalization if enabled
        if self.config.enable_score_normalization:
            ranked_hits = self._normalize_scores(ranked_hits)
        
        # Log scores before filtering
        logger.info(
            "Score distribution before filtering",
            extra={
                "total_hits": len(ranked_hits),
                "min_score_threshold": self.config.min_score_threshold,
                "score_samples": [
                    {"id": hit.id, "score": hit.score, "title": hit.document.get("title", "")[:50]}
                    for hit in ranked_hits[:5]
                ] if ranked_hits else []
            }
        )
        
        # Filter by minimum score threshold
        filtered_hits = [
            hit for hit in ranked_hits 
            if hit.score >= self.config.min_score_threshold
        ]
        
        # Calculate deduplication count
        total_raw_hits = sum(len(result.hits) for result in successful_results)
        deduplication_count = total_raw_hits - len(filtered_hits)
        
        ranking_time = (time.time() - start_time) * 1000
        
        # Update performance metrics
        self._update_performance_metrics(algorithm_to_use, ranking_time, deduplication_count)
        
        logger.info(
            "Result ranking completed",
            extra={
                "total_raw_hits": total_raw_hits,
                "ranked_hits": len(filtered_hits),
                "deduplication_count": deduplication_count,
                "ranking_time_ms": ranking_time,
                "algorithm": algorithm_to_use.value,
                "min_score_threshold": self.config.min_score_threshold
            }
        )
        
        # Create results with A/B testing metadata
        results = RankedResults(
            hits=filtered_hits,
            total_unique_hits=len(filtered_hits),
            deduplication_count=deduplication_count,
            ranking_time_ms=ranking_time,
            ranking_algorithm=algorithm_to_use.value,
            query_context=query_context
        )
        
        # Add A/B testing metadata if active
        if self.config.ab_testing_enabled and session_id:
            for hit in results.hits:
                if hit.ranking_info is None:
                    hit.ranking_info = {}
                hit.ranking_info.update({
                    "ab_test_session_id": session_id,
                    "ab_test_algorithm": algorithm_to_use.value,
                    "ab_test_active": True
                })
        
        return results
    
    def calculate_relevance_score(
        self, 
        result: SearchHit, 
        query_context: QueryContext,
        variant: QueryVariant,
        position: int = 0
    ) -> float:
        """
        Calculate relevance score for a single search result.
        
        Args:
            result: SearchHit object to score
            query_context: Query processing context
            variant: QueryVariant that produced this result
            position: Position of result in original search results
            
        Returns:
            Calculated relevance score
        """
        # Base score from Meilisearch
        base_score = result.score
        
        # Log initial score
        logger.debug(
            "Calculating relevance score",
            extra={
                "document_id": result.id,
                "base_score": base_score,
                "variant_type": variant.variant_type.value,
                "position": position
            }
        )
        
        # Initialize scoring factors
        scoring_factors = {
            "base_score": base_score,
            "variant_boost": 1.0,
            "thai_boost": 1.0,
            "exact_match_boost": 1.0,
            "tokenization_boost": 1.0,
            "position_penalty": 1.0
        }
        
        # Apply variant-specific boosts
        scoring_factors["variant_boost"] = self._calculate_variant_boost(
            variant, query_context
        )
        
        # Apply Thai content boost
        if query_context.thai_content_ratio > 0.5:
            scoring_factors["thai_boost"] = self._get_boost_thai_matches()
        
        # Apply exact match boost
        if self._is_exact_match(result, query_context.original_query):
            scoring_factors["exact_match_boost"] = self._get_boost_exact_matches()
        
        # Apply compound word boost
        if variant.variant_type == QueryVariantType.COMPOUND_SPLIT:
            scoring_factors["exact_match_boost"] *= self._get_boost_compound_matches()
        
        # Apply tokenization confidence boost
        if query_context.tokenization_confidence > 0.8:
            confidence_boost = 1.0 + (
                (query_context.tokenization_confidence - 0.8) * 
                self.config.tokenization_confidence_factor
            )
            scoring_factors["tokenization_boost"] = confidence_boost
        
        # Apply position decay if enabled
        if self.config.position_decay_enabled and position > 0:
            position_penalty = math.exp(-self.config.decay_factor * position)
            scoring_factors["position_penalty"] = position_penalty
        
        # Calculate final score
        final_score = base_score
        for factor_name, factor_value in scoring_factors.items():
            if factor_name != "base_score":
                final_score *= factor_value
        
        # Ensure score doesn't exceed 1.0
        final_score = min(final_score, 1.0)
        
        # Create ranking metadata
        ranking_metadata = RankingMetadata(
            base_score=base_score,
            thai_boost=scoring_factors["thai_boost"],
            exact_match_boost=scoring_factors["exact_match_boost"],
            tokenization_boost=scoring_factors["tokenization_boost"],
            final_score=final_score,
            ranking_factors=scoring_factors
        )
        
        # Update result with ranking information
        if result.ranking_info is None:
            result.ranking_info = {}
        
        result.ranking_info.update({
            "ranking_metadata": ranking_metadata.model_dump(),
            "variant_type": variant.variant_type.value,
            "variant_weight": variant.weight,
            "tokenization_engine": variant.tokenization_engine,
            "position_in_variant": position
        })
        
        return final_score
    
    def _collect_and_score_hits(
        self, 
        search_results: List[SearchResult], 
        query_context: QueryContext
    ) -> List[Tuple[SearchHit, float, QueryVariant, int]]:
        """
        Collect all hits from search results and calculate initial scores.
        
        Returns:
            List of tuples (hit, score, variant, position)
        """
        scored_hits = []
        
        for result in search_results:
            for position, hit in enumerate(result.hits):
                # Calculate relevance score for this hit
                relevance_score = self.calculate_relevance_score(
                    hit, query_context, result.query_variant, position
                )
                
                scored_hits.append((hit, relevance_score, result.query_variant, position))
        
        return scored_hits
    
    def _calculate_content_similarity(self, hit1: SearchHit, hit2: SearchHit) -> float:
        """
        Calculate content similarity between two search hits.
        
        Args:
            hit1: First search hit
            hit2: Second search hit
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Extract text content for comparison
        content1 = self._extract_text_content(hit1)
        content2 = self._extract_text_content(hit2)
        
        if not content1 or not content2:
            return 0.0
        
        # Use sequence matcher for similarity calculation
        similarity = SequenceMatcher(None, content1, content2).ratio()
        
        return similarity
    
    def _extract_text_content(self, hit: SearchHit) -> str:
        """
        Extract text content from a search hit for similarity comparison.
        
        Args:
            hit: Search hit to extract content from
            
        Returns:
            Combined text content from title and content fields
        """
        content_parts = []
        
        # Extract title
        title = hit.document.get("title", "")
        if isinstance(title, str) and title.strip():
            content_parts.append(title.strip())
        
        # Extract content
        content = hit.document.get("content", "")
        if isinstance(content, str) and content.strip():
            # Limit content length for performance
            content_truncated = content.strip()[:500]
            content_parts.append(content_truncated)
        
        return " ".join(content_parts).lower()
    
    def _generate_content_hash(self, hit: SearchHit) -> str:
        """
        Generate a hash of the hit's content for fast duplicate detection.
        
        Args:
            hit: Search hit to hash
            
        Returns:
            MD5 hash of the content
        """
        content = self._extract_text_content(hit)
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _apply_tie_breaking_rules(
        self, 
        tied_hits: List[Tuple[SearchHit, float, QueryVariant, int]]
    ) -> Tuple[SearchHit, float, QueryVariant, int]:
        """
        Apply tie-breaking rules when multiple hits have similar scores.
        
        Args:
            tied_hits: List of hits with similar scores
            
        Returns:
            Best hit based on tie-breaking rules
        """
        if len(tied_hits) == 1:
            return tied_hits[0]
        
        # Sort by multiple criteria for tie-breaking
        def tie_breaking_key(hit_tuple):
            hit, score, variant, position = hit_tuple
            
            # Primary: Higher score
            score_priority = -score
            
            # Secondary: Better variant type (tokenized > original > compound > fallback)
            variant_priority = {
                QueryVariantType.TOKENIZED: 0,
                QueryVariantType.ORIGINAL: 1,
                QueryVariantType.COMPOUND_SPLIT: 2,
                QueryVariantType.FALLBACK: 3
            }.get(variant.variant_type, 4)
            
            # Tertiary: Better tokenization engine
            engine_priority = {
                "newmm": 0,
                "attacut": 1,
                "deepcut": 2,
                "basic": 3
            }.get(variant.tokenization_engine, 4)
            
            # Quaternary: Lower position (earlier in results)
            position_priority = position
            
            # Quinary: Higher variant weight
            weight_priority = -variant.weight
            
            # Senary: Document with more content (prefer comprehensive results)
            content_length = len(self._extract_text_content(hit))
            content_priority = -content_length
            
            return (
                score_priority,
                variant_priority,
                engine_priority,
                position_priority,
                weight_priority,
                content_priority
            )
        
        # Sort and return the best hit
        tied_hits.sort(key=tie_breaking_key)
        best_hit = tied_hits[0]
        
        # Add tie-breaking information to ranking metadata
        hit, score, variant, position = best_hit
        if hit.ranking_info is None:
            hit.ranking_info = {}
        
        hit.ranking_info.update({
            "tie_breaking_applied": True,
            "tied_candidates": len(tied_hits),
            "tie_breaking_winner": {
                "variant_type": variant.variant_type.value,
                "tokenization_engine": variant.tokenization_engine,
                "position": position,
                "variant_weight": variant.weight
            }
        })
        
        return best_hit
    
    def _merge_results_with_content_similarity(
        self, 
        scored_hits: List[Tuple[SearchHit, float, QueryVariant, int]],
        similarity_threshold: float = 0.8
    ) -> List[Tuple[SearchHit, float, QueryVariant, int]]:
        """
        Merge results using both document ID and content similarity.
        
        Args:
            scored_hits: List of scored hits
            similarity_threshold: Threshold for content similarity (0.0-1.0)
            
        Returns:
            Merged list with duplicates removed
        """
        if not scored_hits:
            return []
        
        # First, group by document ID (exact duplicates)
        id_groups: Dict[str, List[Tuple[SearchHit, float, QueryVariant, int]]] = {}
        
        for hit_tuple in scored_hits:
            hit, score, variant, position = hit_tuple
            doc_id = hit.id
            
            if doc_id not in id_groups:
                id_groups[doc_id] = []
            
            id_groups[doc_id].append(hit_tuple)
        
        # Process each ID group to find the best representative
        id_representatives = []
        for doc_id, hits_for_id in id_groups.items():
            if len(hits_for_id) == 1:
                id_representatives.append(hits_for_id[0])
            else:
                # Apply tie-breaking for multiple hits with same ID
                best_hit = self._apply_tie_breaking_rules(hits_for_id)
                
                # Add deduplication metadata
                hit, score, variant, position = best_hit
                if hit.ranking_info is None:
                    hit.ranking_info = {}
                
                hit.ranking_info.update({
                    "id_deduplication_applied": True,
                    "duplicate_variants_count": len(hits_for_id),
                    "duplicate_variants": [
                        {
                            "variant_type": v.variant_type.value,
                            "score": s,
                            "position": p
                        }
                        for _, s, v, p in hits_for_id[:3]  # Top 3 for brevity
                    ]
                })
                
                id_representatives.append(best_hit)
        
        # Now apply content similarity deduplication
        if similarity_threshold < 1.0:
            content_merged = self._apply_content_similarity_deduplication(
                id_representatives, similarity_threshold
            )
            return content_merged
        
        return id_representatives
    
    def _apply_content_similarity_deduplication(
        self, 
        hits: List[Tuple[SearchHit, float, QueryVariant, int]],
        similarity_threshold: float
    ) -> List[Tuple[SearchHit, float, QueryVariant, int]]:
        """
        Apply content similarity-based deduplication.
        
        Args:
            hits: List of hits to deduplicate
            similarity_threshold: Similarity threshold for merging
            
        Returns:
            Deduplicated list of hits
        """
        if len(hits) <= 1:
            return hits
        
        # Create similarity groups
        similarity_groups = []
        processed_indices: Set[int] = set()
        
        for i, hit_tuple_i in enumerate(hits):
            if i in processed_indices:
                continue
            
            # Start a new similarity group
            current_group = [hit_tuple_i]
            processed_indices.add(i)
            
            # Find similar hits
            for j, hit_tuple_j in enumerate(hits[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                hit_i, _, _, _ = hit_tuple_i
                hit_j, _, _, _ = hit_tuple_j
                
                similarity = self._calculate_content_similarity(hit_i, hit_j)
                
                if similarity >= similarity_threshold:
                    current_group.append(hit_tuple_j)
                    processed_indices.add(j)
            
            similarity_groups.append(current_group)
        
        # Select best representative from each similarity group
        final_results = []
        
        for group in similarity_groups:
            if len(group) == 1:
                final_results.append(group[0])
            else:
                # Apply tie-breaking for similar content
                best_hit = self._apply_tie_breaking_rules(group)
                
                # Add similarity deduplication metadata
                hit, score, variant, position = best_hit
                if hit.ranking_info is None:
                    hit.ranking_info = {}
                
                hit.ranking_info.update({
                    "content_similarity_deduplication_applied": True,
                    "similar_content_count": len(group),
                    "similarity_threshold_used": similarity_threshold,
                    "similar_documents": [
                        {
                            "id": h.id,
                            "score": s,
                            "variant_type": v.variant_type.value
                        }
                        for h, s, v, p in group[:3]  # Top 3 for brevity
                    ]
                })
                
                final_results.append(best_hit)
        
        return final_results
    
    def _select_ranking_algorithm(
        self, 
        query_context: QueryContext, 
        session_id: Optional[str] = None
    ) -> RankingAlgorithm:
        """
        Select ranking algorithm based on configuration and A/B testing.
        
        Args:
            query_context: Query processing context
            session_id: Optional session ID for A/B testing
            
        Returns:
            Selected ranking algorithm
        """
        # If A/B testing is not enabled, use configured algorithm
        if not self.config.ab_testing_enabled or not session_id:
            return self.config.algorithm
        
        # Simple hash-based A/B testing assignment
        import hashlib
        hash_input = f"{session_id}_{query_context.original_query}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        assignment_percentage = (hash_value % 100) / 100.0
        
        # Assign to A/B test if within traffic percentage
        if assignment_percentage < self.config.ab_test_traffic_percentage:
            if self.config.ab_test_algorithm:
                algorithm_map = {
                    "weighted_score": RankingAlgorithm.WEIGHTED_SCORE,
                    "optimized_score": RankingAlgorithm.OPTIMIZED_SCORE,
                    "simple_score": RankingAlgorithm.SIMPLE_SCORE,
                    "experimental_score": RankingAlgorithm.EXPERIMENTAL_SCORE
                }
                test_algorithm = algorithm_map.get(
                    self.config.ab_test_algorithm, 
                    RankingAlgorithm.EXPERIMENTAL_SCORE
                )
                
                logger.info(
                    "A/B test assignment",
                    extra={
                        "session_id": session_id,
                        "test_algorithm": test_algorithm.value,
                        "control_algorithm": self.config.algorithm.value,
                        "assignment_percentage": assignment_percentage
                    }
                )
                
                return test_algorithm
        
        # Default to configured algorithm (control group)
        return self.config.algorithm
    
    def _apply_content_type_configuration(self, query_context: QueryContext) -> None:
        """
        Apply content type specific configuration adjustments.
        
        Args:
            query_context: Query processing context to determine content type
        """
        # Determine content type based on query characteristics
        content_type = "mixed"  # Default
        
        if query_context.thai_content_ratio > 0.8:
            if query_context.query_length > 20 and not any(char in query_context.original_query for char in "!@#$%^&*()"):
                content_type = "formal"
            else:
                content_type = "informal"
        elif query_context.thai_content_ratio < 0.2:
            content_type = "mixed"  # Treat English as mixed for now
        
        # Apply content type specific boosts
        if content_type in self.config.content_type_configs:
            type_config = self.config.content_type_configs[content_type]
            
            # Store content-type specific boosts temporarily
            self._content_type_boosts = {
                "exact": type_config.get("boost_exact_matches", self.config.boost_exact_matches),
                "thai": type_config.get("boost_thai_matches", self.config.boost_thai_matches),
                "compound": type_config.get("boost_compound_matches", self.config.boost_compound_matches)
            }
            
            logger.debug(
                "Applied content type configuration",
                extra={
                    "content_type": content_type,
                    "thai_content_ratio": query_context.thai_content_ratio,
                    "query_length": query_context.query_length,
                    "boost_adjustments": type_config
                }
            )
        else:
            # Use default boosts
            self._content_type_boosts = None
    
    def _get_boost_exact_matches(self) -> float:
        """Get effective boost for exact matches."""
        if hasattr(self, '_content_type_boosts') and self._content_type_boosts:
            return self._content_type_boosts["exact"]
        return self.config.boost_exact_matches
    
    def _get_boost_thai_matches(self) -> float:
        """Get effective boost for Thai matches."""
        if hasattr(self, '_content_type_boosts') and self._content_type_boosts:
            return self._content_type_boosts["thai"]
        return self.config.boost_thai_matches
    
    def _get_boost_compound_matches(self) -> float:
        """Get effective boost for compound matches."""
        if hasattr(self, '_content_type_boosts') and self._content_type_boosts:
            return self._content_type_boosts["compound"]
        return self.config.boost_compound_matches
    
    def _update_performance_metrics(
        self, 
        algorithm: RankingAlgorithm, 
        ranking_time: float, 
        deduplication_count: int
    ) -> None:
        """
        Update performance metrics for monitoring and optimization.
        
        Args:
            algorithm: Algorithm used for ranking
            ranking_time: Time taken for ranking in milliseconds
            deduplication_count: Number of duplicates removed
        """
        self._performance_metrics["total_rankings"] += 1
        self._performance_metrics["total_ranking_time_ms"] += ranking_time
        self._performance_metrics["algorithm_usage"][algorithm.value] += 1
        self._performance_metrics["deduplication_stats"]["total_duplicates_removed"] += deduplication_count
        
        # Track algorithm performance for A/B testing
        if algorithm.value not in self._performance_metrics["ab_test_stats"]["algorithm_performance"]:
            self._performance_metrics["ab_test_stats"]["algorithm_performance"][algorithm.value] = {
                "total_uses": 0,
                "total_time_ms": 0.0,
                "avg_time_ms": 0.0,
                "total_duplicates_removed": 0
            }
        
        alg_stats = self._performance_metrics["ab_test_stats"]["algorithm_performance"][algorithm.value]
        alg_stats["total_uses"] += 1
        alg_stats["total_time_ms"] += ranking_time
        alg_stats["avg_time_ms"] = alg_stats["total_time_ms"] / alg_stats["total_uses"]
        alg_stats["total_duplicates_removed"] += deduplication_count
    
    def configure_ab_test(
        self, 
        test_algorithm: str, 
        traffic_percentage: float,
        enabled: bool = True
    ) -> None:
        """
        Configure A/B testing for ranking algorithms.
        
        Args:
            test_algorithm: Algorithm to test against the control
            traffic_percentage: Percentage of traffic to assign to test (0.0-1.0)
            enabled: Whether to enable A/B testing
        """
        if traffic_percentage < 0.0 or traffic_percentage > 1.0:
            raise ValueError("Traffic percentage must be between 0.0 and 1.0")
        
        valid_algorithms = [alg.value for alg in RankingAlgorithm]
        if test_algorithm not in valid_algorithms:
            raise ValueError(f"Invalid test algorithm. Must be one of: {valid_algorithms}")
        
        self.config.ab_testing_enabled = enabled
        self.config.ab_test_algorithm = test_algorithm
        self.config.ab_test_traffic_percentage = traffic_percentage
        
        logger.info(
            "A/B test configuration updated",
            extra={
                "enabled": enabled,
                "test_algorithm": test_algorithm,
                "traffic_percentage": traffic_percentage,
                "control_algorithm": self.config.algorithm.value
            }
        )
    
    def configure_content_type_boosts(
        self, 
        content_type: str, 
        boost_config: Dict[str, float]
    ) -> None:
        """
        Configure content type specific boost parameters.
        
        Args:
            content_type: Content type to configure ("formal", "informal", "mixed")
            boost_config: Dictionary of boost parameters
        """
        valid_content_types = ["formal", "informal", "mixed"]
        if content_type not in valid_content_types:
            raise ValueError(f"Invalid content type. Must be one of: {valid_content_types}")
        
        valid_boost_keys = ["boost_exact_matches", "boost_thai_matches", "boost_compound_matches"]
        for key in boost_config:
            if key not in valid_boost_keys:
                raise ValueError(f"Invalid boost key '{key}'. Must be one of: {valid_boost_keys}")
            if not isinstance(boost_config[key], (int, float)) or boost_config[key] < 1.0:
                raise ValueError(f"Boost value for '{key}' must be a number >= 1.0")
        
        self.config.content_type_configs[content_type] = boost_config
        
        logger.info(
            "Content type configuration updated",
            extra={
                "content_type": content_type,
                "boost_config": boost_config
            }
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics for monitoring and optimization.
        
        Returns:
            Dictionary containing performance metrics
        """
        metrics = self._performance_metrics.copy()
        
        # Calculate derived metrics
        if metrics["total_rankings"] > 0:
            metrics["avg_ranking_time_ms"] = metrics["total_ranking_time_ms"] / metrics["total_rankings"]
            metrics["avg_duplicates_per_ranking"] = (
                metrics["deduplication_stats"]["total_duplicates_removed"] / metrics["total_rankings"]
            )
        else:
            metrics["avg_ranking_time_ms"] = 0.0
            metrics["avg_duplicates_per_ranking"] = 0.0
        
        # Add configuration information
        metrics["current_config"] = {
            "algorithm": self.config.algorithm.value,
            "ab_testing_enabled": self.config.ab_testing_enabled,
            "ab_test_algorithm": self.config.ab_test_algorithm,
            "ab_test_traffic_percentage": self.config.ab_test_traffic_percentage,
            "content_type_configs": self.config.content_type_configs,
            "similarity_threshold": self.config.similarity_threshold,
            "enable_content_similarity_deduplication": self.config.enable_content_similarity_deduplication
        }
        
        return metrics
    
    def optimize_performance(self) -> Dict[str, Any]:
        """
        Analyze performance metrics and suggest optimizations.
        
        Returns:
            Dictionary containing optimization recommendations
        """
        metrics = self.get_performance_metrics()
        recommendations = []
        
        # Analyze ranking time performance
        avg_time = metrics.get("avg_ranking_time_ms", 0)
        if avg_time > 50:  # Target: < 50ms
            recommendations.append({
                "type": "performance",
                "issue": "High average ranking time",
                "current_value": avg_time,
                "target_value": 50,
                "suggestion": "Consider using optimized_score algorithm or reducing similarity threshold"
            })
        
        # Analyze algorithm performance
        alg_performance = metrics["ab_test_stats"]["algorithm_performance"]
        if len(alg_performance) > 1:
            # Find fastest algorithm
            fastest_alg = min(
                alg_performance.items(),
                key=lambda x: x[1]["avg_time_ms"]
            )
            
            current_alg_stats = alg_performance.get(self.config.algorithm.value)
            if current_alg_stats and current_alg_stats["avg_time_ms"] > fastest_alg[1]["avg_time_ms"] * 1.2:
                recommendations.append({
                    "type": "algorithm",
                    "issue": "Suboptimal algorithm performance",
                    "current_algorithm": self.config.algorithm.value,
                    "current_avg_time": current_alg_stats["avg_time_ms"],
                    "recommended_algorithm": fastest_alg[0],
                    "recommended_avg_time": fastest_alg[1]["avg_time_ms"],
                    "suggestion": f"Consider switching to {fastest_alg[0]} for better performance"
                })
        
        # Analyze deduplication effectiveness
        avg_duplicates = metrics.get("avg_duplicates_per_ranking", 0)
        if avg_duplicates > 10:
            recommendations.append({
                "type": "deduplication",
                "issue": "High duplicate count",
                "current_value": avg_duplicates,
                "suggestion": "Consider adjusting similarity threshold or improving query variant generation"
            })
        
        return {
            "analysis_timestamp": time.time(),
            "total_rankings_analyzed": metrics["total_rankings"],
            "recommendations": recommendations,
            "current_performance": {
                "avg_ranking_time_ms": avg_time,
                "avg_duplicates_per_ranking": avg_duplicates,
                "most_used_algorithm": max(metrics["algorithm_usage"].items(), key=lambda x: x[1])[0] if metrics["algorithm_usage"] else None
            }
        }
    
    def _weighted_score_algorithm(
        self, 
        scored_hits: List[Tuple[SearchHit, float, QueryVariant, int]], 
        query_context: QueryContext
    ) -> List[SearchHit]:
        """
        Weighted scoring algorithm with enhanced deduplication and merging.
        
        This algorithm uses both document ID and content similarity for deduplication,
        applies sophisticated tie-breaking rules, and considers variant weights.
        """
        # Apply enhanced deduplication with content similarity
        merged_hits = self._merge_results_with_content_similarity(
            scored_hits, 
            similarity_threshold=0.85  # High threshold for content similarity
        )
        
        # Apply final scoring with variant weights
        final_hits = []
        
        for hit, score, variant, position in merged_hits:
            # Apply variant weight to final score
            weighted_score = score * variant.weight * self.config.variant_weight_factor
            
            # Update hit score
            hit.score = weighted_score
            
            # Add comprehensive ranking information
            if hit.ranking_info is None:
                hit.ranking_info = {}
            
            hit.ranking_info.update({
                "algorithm": "weighted_score",
                "base_score": score,
                "variant_weight": variant.weight,
                "variant_weight_factor": self.config.variant_weight_factor,
                "weighted_final_score": weighted_score,
                "best_variant_type": variant.variant_type.value,
                "tokenization_engine": variant.tokenization_engine,
                "position_in_variant": position
            })
            
            final_hits.append(hit)
        
        # Sort by final weighted score
        final_hits.sort(key=lambda hit: hit.score, reverse=True)
        
        return final_hits
    
    def _optimized_score_algorithm(
        self, 
        scored_hits: List[Tuple[SearchHit, float, QueryVariant, int]], 
        query_context: QueryContext
    ) -> List[SearchHit]:
        """
        Optimized scoring algorithm for production use with better performance.
        
        Uses efficient ID-based deduplication with basic tie-breaking for speed.
        """
        # Use efficient ID-based deduplication only (no content similarity for performance)
        hit_map = {}
        
        for hit, score, variant, position in scored_hits:
            doc_id = hit.id
            
            # Apply variant weight immediately
            weighted_score = score * variant.weight
            
            # Keep only the best scoring version for each document
            if doc_id not in hit_map:
                hit_map[doc_id] = (hit, weighted_score, variant, position)
            else:
                # Apply basic tie-breaking rules
                current_hit, current_score, current_variant, current_position = hit_map[doc_id]
                
                # Prefer higher score, then better variant type, then lower position
                should_replace = (
                    weighted_score > current_score or
                    (weighted_score == current_score and 
                     self._compare_variants_for_tie_breaking(variant, current_variant)) or
                    (weighted_score == current_score and 
                     variant.variant_type == current_variant.variant_type and
                     position < current_position)
                )
                
                if should_replace:
                    hit_map[doc_id] = (hit, weighted_score, variant, position)
        
        # Extract hits and update scores
        final_hits = []
        for hit, score, variant, position in hit_map.values():
            hit.score = score
            
            # Add minimal ranking info for performance
            if hit.ranking_info is None:
                hit.ranking_info = {}
            
            hit.ranking_info.update({
                "algorithm": "optimized_score",
                "variant_type": variant.variant_type.value,
                "tokenization_engine": variant.tokenization_engine,
                "final_score": score,
                "deduplication_method": "id_based_only"
            })
            
            final_hits.append(hit)
        
        # Sort by score
        final_hits.sort(key=lambda hit: hit.score, reverse=True)
        
        return final_hits
    
    def _compare_variants_for_tie_breaking(
        self, 
        variant1: QueryVariant, 
        variant2: QueryVariant
    ) -> bool:
        """
        Compare two variants for tie-breaking purposes.
        
        Args:
            variant1: First variant to compare
            variant2: Second variant to compare
            
        Returns:
            True if variant1 should be preferred over variant2
        """
        # Define variant type priority (lower number = higher priority)
        variant_priority = {
            QueryVariantType.TOKENIZED: 0,
            QueryVariantType.ORIGINAL: 1,
            QueryVariantType.COMPOUND_SPLIT: 2,
            QueryVariantType.FALLBACK: 3
        }
        
        priority1 = variant_priority.get(variant1.variant_type, 4)
        priority2 = variant_priority.get(variant2.variant_type, 4)
        
        if priority1 != priority2:
            return priority1 < priority2
        
        # If same variant type, prefer better tokenization engine
        engine_priority = {
            "newmm": 0,
            "attacut": 1,
            "deepcut": 2,
            "basic": 3
        }
        
        engine1_priority = engine_priority.get(variant1.tokenization_engine, 4)
        engine2_priority = engine_priority.get(variant2.tokenization_engine, 4)
        
        if engine1_priority != engine2_priority:
            return engine1_priority < engine2_priority
        
        # If same engine, prefer higher weight
        return variant1.weight > variant2.weight
    
    def _simple_score_algorithm(
        self, 
        scored_hits: List[Tuple[SearchHit, float, QueryVariant, int]], 
        query_context: QueryContext
    ) -> List[SearchHit]:
        """
        Simple scoring algorithm that uses basic deduplication and scoring.
        """
        # Simple ID-based deduplication, keeping highest score
        seen_ids = {}
        
        for hit, score, variant, position in scored_hits:
            doc_id = hit.id
            
            if doc_id not in seen_ids or score > seen_ids[doc_id].score:
                hit.score = score
                seen_ids[doc_id] = hit
        
        # Convert to list and sort
        final_hits = list(seen_ids.values())
        final_hits.sort(key=lambda hit: hit.score, reverse=True)
        
        return final_hits
    
    def _experimental_score_algorithm(
        self, 
        scored_hits: List[Tuple[SearchHit, float, QueryVariant, int]], 
        query_context: QueryContext
    ) -> List[SearchHit]:
        """
        Experimental scoring algorithm for testing new approaches.
        """
        # This algorithm can be used for A/B testing new ranking approaches
        # For now, it's similar to weighted but with different parameters
        
        # Apply experimental boosting factors
        experimental_boost = 1.2 if query_context.thai_content_ratio > 0.7 else 1.0
        
        hit_groups = {}
        
        for hit, score, variant, position in scored_hits:
            doc_id = hit.id
            
            # Apply experimental boost
            experimental_score = score * experimental_boost
            
            if doc_id not in hit_groups:
                hit_groups[doc_id] = []
            
            hit_groups[doc_id].append((hit, experimental_score, variant, position))
        
        # Select best hit for each document
        final_hits = []
        
        for doc_id, hits_for_doc in hit_groups.items():
            hits_for_doc.sort(key=lambda x: x[1], reverse=True)
            best_hit, best_score, best_variant, best_position = hits_for_doc[0]
            
            best_hit.score = best_score
            
            if best_hit.ranking_info is None:
                best_hit.ranking_info = {}
            
            best_hit.ranking_info.update({
                "algorithm": "experimental_score",
                "experimental_boost": experimental_boost,
                "variant_type": best_variant.variant_type.value
            })
            
            final_hits.append(best_hit)
        
        final_hits.sort(key=lambda hit: hit.score, reverse=True)
        
        return final_hits
    
    def _calculate_variant_boost(
        self, 
        variant: QueryVariant, 
        query_context: QueryContext
    ) -> float:
        """Calculate boost factor based on variant characteristics."""
        boost = 1.0
        
        # Boost based on variant type
        if variant.variant_type == QueryVariantType.ORIGINAL:
            boost *= 1.1  # Slight boost for original query
        elif variant.variant_type == QueryVariantType.TOKENIZED:
            boost *= 1.2  # Higher boost for tokenized queries
        elif variant.variant_type == QueryVariantType.COMPOUND_SPLIT:
            boost *= self._get_boost_compound_matches()
        elif variant.variant_type == QueryVariantType.FALLBACK:
            boost *= 0.8  # Lower boost for fallback queries
        
        # Boost based on tokenization engine quality
        if variant.tokenization_engine == "newmm":
            boost *= 1.1  # Best engine gets boost
        elif variant.tokenization_engine in ["attacut", "deepcut"]:
            boost *= 1.0  # Standard engines
        else:
            boost *= 0.9  # Unknown engines get penalty
        
        return boost
    
    def _is_exact_match(self, result: SearchHit, original_query: str) -> bool:
        """Check if result contains exact match for original query."""
        # Simple exact match detection
        # In a more sophisticated implementation, this could check specific fields
        
        query_lower = original_query.lower().strip()
        
        # Check title field
        title = result.document.get("title", "")
        if isinstance(title, str) and query_lower in title.lower():
            return True
        
        # Check content field
        content = result.document.get("content", "")
        if isinstance(content, str) and query_lower in content.lower():
            return True
        
        return False
    
    def _normalize_scores(self, hits: List[SearchHit]) -> List[SearchHit]:
        """Normalize scores to 0-1 range."""
        if not hits:
            return hits
        
        # Find max score
        max_score = max(hit.score for hit in hits)
        
        if max_score <= 0:
            return hits
        
        # Normalize all scores
        for hit in hits:
            hit.score = hit.score / max_score
            
            # Update ranking info
            if hit.ranking_info is None:
                hit.ranking_info = {}
            
            hit.ranking_info["normalized"] = True
            hit.ranking_info["normalization_factor"] = max_score
        
        return hits
    
    def _create_query_context(
        self, 
        original_query: str, 
        search_results: List[SearchResult]
    ) -> QueryContext:
        """Create QueryContext from available information."""
        # Analyze query for Thai content
        thai_chars = sum(1 for char in original_query if '\u0e00' <= char <= '\u0e7f')
        thai_content_ratio = thai_chars / len(original_query) if original_query else 0.0
        
        # Determine primary language
        if thai_content_ratio > 0.7:
            primary_language = "thai"
        elif thai_content_ratio > 0.3:
            primary_language = "mixed"
        else:
            primary_language = "english"
        
        # Calculate average tokenization confidence from variants
        tokenization_confidence = 0.8  # Default confidence
        
        # Extract processed query (use first tokenized variant if available)
        processed_query = original_query
        for result in search_results:
            if result.query_variant.variant_type == QueryVariantType.TOKENIZED:
                processed_query = result.query_variant.query_text
                break
        
        return QueryContext(
            original_query=original_query,
            processed_query=processed_query,
            thai_content_ratio=thai_content_ratio,
            query_length=len(original_query),
            tokenization_confidence=tokenization_confidence,
            primary_language=primary_language,
            search_intent=None
        )
    
    def _create_empty_ranked_results(
        self, 
        original_query: str, 
        query_context: Optional[QueryContext]
    ) -> RankedResults:
        """Create empty RankedResults for error cases."""
        if query_context is None:
            query_context = self._create_query_context(original_query, [])
        
        return RankedResults(
            hits=[],
            total_unique_hits=0,
            deduplication_count=0,
            ranking_time_ms=0.0,
            ranking_algorithm=self.config.algorithm.value,
            query_context=query_context
        )
    
    def update_config(self, new_config: RankingConfig) -> None:
        """Update ranking configuration."""
        old_algorithm = self.config.algorithm
        self.config = ExtendedRankingConfig(new_config)
        
        logger.info(
            "ResultRanker configuration updated",
            extra={
                "old_algorithm": old_algorithm.value,
                "new_algorithm": new_config.algorithm.value,
                "boost_exact_matches": new_config.boost_exact_matches,
                "boost_thai_matches": new_config.boost_thai_matches,
                "boost_compound_matches": new_config.boost_compound_matches
            }
        )
    
    def get_ranking_stats(self) -> Dict[str, Any]:
        """Get comprehensive ranking statistics and configuration."""
        return {
            "algorithm": self.config.algorithm.value,
            "configuration": {
                "boost_exact_matches": self._get_boost_exact_matches(),
                "boost_thai_matches": self._get_boost_thai_matches(),
                "boost_compound_matches": self._get_boost_compound_matches(),
                "decay_factor": self.config.decay_factor,
                "min_score_threshold": self.config.min_score_threshold,
                "max_results_per_variant": self.config.max_results_per_variant,
                "enable_score_normalization": self.config.enable_score_normalization,
                "position_decay_enabled": self.config.position_decay_enabled,
                "variant_weight_factor": self.config.variant_weight_factor,
                "tokenization_confidence_factor": self.config.tokenization_confidence_factor,
                "similarity_threshold": self.config.similarity_threshold,
                "enable_content_similarity_deduplication": self.config.enable_content_similarity_deduplication,
                "enable_performance_optimization": self.config.enable_performance_optimization
            },
            "ab_testing": {
                "enabled": self.config.ab_testing_enabled,
                "test_algorithm": self.config.ab_test_algorithm,
                "traffic_percentage": self.config.ab_test_traffic_percentage,
                "session_id": self.config.ab_test_session_id
            },
            "content_type_configs": self.config.content_type_configs,
            "available_algorithms": [alg.value for alg in RankingAlgorithm],
            "performance_metrics": self.get_performance_metrics()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the result ranker."""
        try:
            # Test basic functionality with dummy data
            test_context = QueryContext(
                original_query="test",
                processed_query="test",
                thai_content_ratio=0.0,
                query_length=4,
                tokenization_confidence=0.8,
                primary_language="english"
            )
            
            # This should not raise an exception
            _ = self._create_empty_ranked_results("test", test_context)
            
            return {
                "status": "healthy",
                "algorithm": self.config.algorithm.value,
                "configuration_valid": True
            }
            
        except Exception as e:
            logger.error(f"ResultRanker health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "algorithm": self.config.algorithm.value
            }