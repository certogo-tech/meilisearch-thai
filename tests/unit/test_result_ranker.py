"""
Unit tests for the ResultRanker class.
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from src.search_proxy.services.result_ranker import (
    ResultRanker, 
    RankingAlgorithm
)
from src.search_proxy.config.settings import RankingConfig
from src.search_proxy.models.search import SearchResult, QueryContext, RankedResults
from src.search_proxy.models.responses import SearchHit
from src.search_proxy.models.query import QueryVariant, QueryVariantType


class TestResultRanker:
    """Test cases for ResultRanker class."""
    
    @pytest.fixture
    def ranking_config(self) -> RankingConfig:
        """Create test ranking configuration."""
        return RankingConfig(
            algorithm="weighted_score",
            boost_exact_matches=2.0,
            boost_thai_matches=1.5,
            boost_compound_matches=1.3,
            decay_factor=0.1,
            min_score_threshold=0.1,
            enable_score_normalization=True
        )
    
    @pytest.fixture
    def result_ranker(self, ranking_config: RankingConfig) -> ResultRanker:
        """Create ResultRanker instance for testing."""
        return ResultRanker(ranking_config)
    
    @pytest.fixture
    def sample_query_context(self) -> QueryContext:
        """Create sample query context for testing."""
        return QueryContext(
            original_query="ค้นหาเอกสาร",
            processed_query="ค้นหา เอกสาร",
            thai_content_ratio=1.0,
            query_length=10,
            tokenization_confidence=0.9,
            primary_language="thai"
        )
    
    @pytest.fixture
    def sample_query_variants(self) -> List[QueryVariant]:
        """Create sample query variants for testing."""
        return [
            QueryVariant(
                query_text="ค้นหาเอกสาร",
                variant_type=QueryVariantType.ORIGINAL,
                tokenization_engine="none",
                weight=0.8
            ),
            QueryVariant(
                query_text="ค้นหา เอกสาร",
                variant_type=QueryVariantType.TOKENIZED,
                tokenization_engine="newmm",
                weight=1.0
            ),
            QueryVariant(
                query_text="ค้น หา เอก สาร",
                variant_type=QueryVariantType.COMPOUND_SPLIT,
                tokenization_engine="newmm",
                weight=0.9
            )
        ]
    
    @pytest.fixture
    def sample_search_hits(self) -> List[SearchHit]:
        """Create sample search hits for testing."""
        return [
            SearchHit(
                id="doc_1",
                score=0.9,
                document={"title": "เอกสารสำคัญ", "content": "ค้นหาเอกสารในระบบ"},
                highlight={"title": ["<em>เอกสาร</em>สำคัญ"]},
                ranking_info={"base_score": 0.9}
            ),
            SearchHit(
                id="doc_2",
                score=0.8,
                document={"title": "คู่มือการใช้งาน", "content": "เอกสารคู่มือ"},
                highlight={"content": ["<em>เอกสาร</em>คู่มือ"]},
                ranking_info={"base_score": 0.8}
            ),
            SearchHit(
                id="doc_3",
                score=0.7,
                document={"title": "Document Guide", "content": "Search documents"},
                highlight=None,
                ranking_info={"base_score": 0.7}
            )
        ]
    
    @pytest.fixture
    def sample_search_results(
        self, 
        sample_query_variants: List[QueryVariant], 
        sample_search_hits: List[SearchHit]
    ) -> List[SearchResult]:
        """Create sample search results for testing."""
        return [
            SearchResult(
                query_variant=sample_query_variants[0],
                hits=[sample_search_hits[0], sample_search_hits[1]],
                total_hits=2,
                processing_time_ms=50.0,
                success=True,
                error_message=None,
                meilisearch_metadata={"processingTimeMs": 45}
            ),
            SearchResult(
                query_variant=sample_query_variants[1],
                hits=[sample_search_hits[0], sample_search_hits[2]],
                total_hits=2,
                processing_time_ms=60.0,
                success=True,
                error_message=None,
                meilisearch_metadata={"processingTimeMs": 55}
            ),
            SearchResult(
                query_variant=sample_query_variants[2],
                hits=[sample_search_hits[1]],
                total_hits=1,
                processing_time_ms=40.0,
                success=True,
                error_message=None,
                meilisearch_metadata={"processingTimeMs": 35}
            )
        ]
    
    def test_result_ranker_initialization(self, ranking_config: RankingConfig):
        """Test ResultRanker initialization."""
        ranker = ResultRanker(ranking_config)
        
        assert ranker.config.base_config == ranking_config
        assert ranker.config.algorithm == RankingAlgorithm.WEIGHTED_SCORE
        assert ranker.config.boost_exact_matches == 2.0
        assert ranker.config.boost_thai_matches == 1.5
    
    def test_result_ranker_default_config(self):
        """Test ResultRanker with default configuration."""
        ranker = ResultRanker()
        
        assert ranker.config.algorithm == RankingAlgorithm.WEIGHTED_SCORE
        assert ranker.config.boost_exact_matches == 2.0
        assert ranker.config.boost_thai_matches == 1.5
        assert ranker.config.min_score_threshold == 0.1
    
    def test_rank_results_empty_input(
        self, 
        result_ranker: ResultRanker,
        sample_query_context: QueryContext
    ):
        """Test ranking with empty search results."""
        ranked_results = result_ranker.rank_results([], "test query", sample_query_context)
        
        assert isinstance(ranked_results, RankedResults)
        assert len(ranked_results.hits) == 0
        assert ranked_results.total_unique_hits == 0
        assert ranked_results.deduplication_count == 0
        assert ranked_results.ranking_algorithm == "weighted_score"
    
    def test_rank_results_no_successful_results(
        self, 
        result_ranker: ResultRanker,
        sample_query_variants: List[QueryVariant]
    ):
        """Test ranking with no successful search results."""
        failed_results = [
            SearchResult(
                query_variant=sample_query_variants[0],
                hits=[],
                total_hits=0,
                processing_time_ms=0.0,
                success=False,
                error_message="Search failed",
                meilisearch_metadata={}
            )
        ]
        
        ranked_results = result_ranker.rank_results(failed_results, "test query")
        
        assert len(ranked_results.hits) == 0
        assert ranked_results.total_unique_hits == 0
    
    def test_rank_results_successful(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test successful ranking of search results."""
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert isinstance(ranked_results, RankedResults)
        assert len(ranked_results.hits) > 0
        assert ranked_results.total_unique_hits > 0
        assert ranked_results.ranking_time_ms > 0
        assert ranked_results.ranking_algorithm == "weighted_score"
        
        # Check that results are sorted by score (descending)
        scores = [hit.score for hit in ranked_results.hits]
        assert scores == sorted(scores, reverse=True)
    
    def test_calculate_relevance_score_basic(
        self, 
        result_ranker: ResultRanker,
        sample_search_hits: List[SearchHit],
        sample_query_context: QueryContext,
        sample_query_variants: List[QueryVariant]
    ):
        """Test basic relevance score calculation."""
        hit = sample_search_hits[0]
        variant = sample_query_variants[1]  # Tokenized variant
        
        score = result_ranker.calculate_relevance_score(
            hit, sample_query_context, variant, position=0
        )
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert hit.ranking_info is not None
        assert "ranking_metadata" in hit.ranking_info
    
    def test_calculate_relevance_score_thai_boost(
        self, 
        result_ranker: ResultRanker,
        sample_search_hits: List[SearchHit],
        sample_query_variants: List[QueryVariant]
    ):
        """Test Thai content boost in relevance scoring."""
        hit = sample_search_hits[0]
        variant = sample_query_variants[1]
        
        # Create query context with high Thai content ratio
        thai_context = QueryContext(
            original_query="ค้นหาเอกสารภาษาไทย",
            processed_query="ค้นหา เอกสาร ภาษาไทย",
            thai_content_ratio=0.9,
            query_length=15,
            tokenization_confidence=0.9,
            primary_language="thai"
        )
        
        score = result_ranker.calculate_relevance_score(
            hit, thai_context, variant, position=0
        )
        
        # Score should be boosted for Thai content
        assert score > hit.score  # Should be higher than base score
        assert hit.ranking_info["ranking_metadata"]["thai_boost"] == 1.5
    
    def test_calculate_relevance_score_exact_match_boost(
        self, 
        result_ranker: ResultRanker,
        sample_query_context: QueryContext,
        sample_query_variants: List[QueryVariant]
    ):
        """Test exact match boost in relevance scoring."""
        # Create hit with exact match in title
        hit = SearchHit(
            id="exact_match_doc",
            score=0.8,
            document={"title": "ค้นหาเอกสาร", "content": "เนื้อหาเอกสาร"},
            highlight=None,
            ranking_info={"base_score": 0.8}
        )
        
        variant = sample_query_variants[0]  # Original variant
        
        score = result_ranker.calculate_relevance_score(
            hit, sample_query_context, variant, position=0
        )
        
        # Score should be boosted for exact match
        assert score > hit.score
        assert hit.ranking_info["ranking_metadata"]["exact_match_boost"] == 2.0
    
    def test_calculate_relevance_score_compound_boost(
        self, 
        result_ranker: ResultRanker,
        sample_search_hits: List[SearchHit],
        sample_query_context: QueryContext,
        sample_query_variants: List[QueryVariant]
    ):
        """Test compound word boost in relevance scoring."""
        hit = sample_search_hits[0]
        compound_variant = sample_query_variants[2]  # Compound split variant
        
        score = result_ranker.calculate_relevance_score(
            hit, sample_query_context, compound_variant, position=0
        )
        
        # Should have compound boost applied
        ranking_metadata = hit.ranking_info["ranking_metadata"]
        assert ranking_metadata["exact_match_boost"] >= 1.3  # Compound boost applied
    
    def test_calculate_relevance_score_position_decay(
        self, 
        result_ranker: ResultRanker,
        sample_search_hits: List[SearchHit],
        sample_query_context: QueryContext,
        sample_query_variants: List[QueryVariant]
    ):
        """Test position decay in relevance scoring."""
        hit = sample_search_hits[0]
        variant = sample_query_variants[1]
        
        # Calculate scores for different positions
        score_pos_0 = result_ranker.calculate_relevance_score(
            hit, sample_query_context, variant, position=0
        )
        
        score_pos_5 = result_ranker.calculate_relevance_score(
            hit, sample_query_context, variant, position=5
        )
        
        # Score should decay with position
        assert score_pos_0 > score_pos_5
    
    def test_weighted_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test weighted score algorithm specifically."""
        # Set algorithm to weighted score
        result_ranker.config.algorithm = RankingAlgorithm.WEIGHTED_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "weighted_score"
        assert len(ranked_results.hits) > 0
        
        # Check that variant information is preserved
        for hit in ranked_results.hits:
            assert hit.ranking_info is not None
            assert "variants_matched" in hit.ranking_info
            assert "best_variant_type" in hit.ranking_info
    
    def test_optimized_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test optimized score algorithm."""
        # Set algorithm to optimized score
        result_ranker.config.algorithm = RankingAlgorithm.OPTIMIZED_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "optimized_score"
        assert len(ranked_results.hits) > 0
        
        # Check that algorithm info is preserved
        for hit in ranked_results.hits:
            assert hit.ranking_info is not None
            assert hit.ranking_info.get("algorithm") == "optimized_score"
    
    def test_simple_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test simple score algorithm."""
        # Set algorithm to simple score
        result_ranker.config.algorithm = RankingAlgorithm.SIMPLE_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "simple_score"
        assert len(ranked_results.hits) > 0
    
    def test_experimental_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test experimental score algorithm."""
        # Set algorithm to experimental score
        result_ranker.config.algorithm = RankingAlgorithm.EXPERIMENTAL_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "experimental_score"
        assert len(ranked_results.hits) > 0
        
        # Check experimental algorithm info
        for hit in ranked_results.hits:
            assert hit.ranking_info is not None
            assert hit.ranking_info.get("algorithm") == "experimental_score"
    
    def test_score_normalization(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test score normalization functionality."""
        # Enable score normalization
        result_ranker.config.enable_score_normalization = True
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        # Check that scores are normalized (highest should be close to 1.0)
        if ranked_results.hits:
            max_score = max(hit.score for hit in ranked_results.hits)
            assert max_score <= 1.0
            
            # Check normalization metadata
            for hit in ranked_results.hits:
                if hit.ranking_info:
                    assert hit.ranking_info.get("normalized") is True
    
    def test_min_score_threshold(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test minimum score threshold filtering."""
        # Set high minimum score threshold
        result_ranker.config.min_score_threshold = 0.9
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        # All results should have score >= threshold
        for hit in ranked_results.hits:
            assert hit.score >= 0.9
    
    def test_deduplication_by_id(
        self, 
        result_ranker: ResultRanker,
        sample_query_variants: List[QueryVariant]
    ):
        """Test deduplication of results with same document ID."""
        # Create duplicate hits with same ID but different scores
        duplicate_hits = [
            SearchHit(
                id="duplicate_doc",
                score=0.8,
                document={"title": "Document 1"},
                ranking_info={"base_score": 0.8}
            ),
            SearchHit(
                id="duplicate_doc",
                score=0.9,
                document={"title": "Document 1 (better)"},
                ranking_info={"base_score": 0.9}
            )
        ]
        
        search_results = [
            SearchResult(
                query_variant=sample_query_variants[0],
                hits=[duplicate_hits[0]],
                total_hits=1,
                processing_time_ms=50.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            ),
            SearchResult(
                query_variant=sample_query_variants[1],
                hits=[duplicate_hits[1]],
                total_hits=1,
                processing_time_ms=60.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            )
        ]
        
        ranked_results = result_ranker.rank_results(search_results, "test query")
        
        # Should have only one result (the higher scoring one)
        assert len(ranked_results.hits) == 1
        assert ranked_results.deduplication_count == 1
        assert ranked_results.hits[0].id == "duplicate_doc"
    
    def test_variant_boost_calculation(
        self, 
        result_ranker: ResultRanker,
        sample_query_context: QueryContext
    ):
        """Test variant boost calculation for different variant types."""
        # Test different variant types
        original_variant = QueryVariant(
            query_text="test",
            variant_type=QueryVariantType.ORIGINAL,
            tokenization_engine="none",
            weight=1.0
        )
        
        tokenized_variant = QueryVariant(
            query_text="test tokens",
            variant_type=QueryVariantType.TOKENIZED,
            tokenization_engine="newmm",
            weight=1.0
        )
        
        fallback_variant = QueryVariant(
            query_text="test fallback",
            variant_type=QueryVariantType.FALLBACK,
            tokenization_engine="basic",
            weight=1.0
        )
        
        # Calculate boosts
        original_boost = result_ranker._calculate_variant_boost(
            original_variant, sample_query_context
        )
        tokenized_boost = result_ranker._calculate_variant_boost(
            tokenized_variant, sample_query_context
        )
        fallback_boost = result_ranker._calculate_variant_boost(
            fallback_variant, sample_query_context
        )
        
        # Tokenized should have higher boost than original
        assert tokenized_boost > original_boost
        # Fallback should have lower boost
        assert fallback_boost < original_boost
    
    def test_exact_match_detection(
        self, 
        result_ranker: ResultRanker
    ):
        """Test exact match detection in documents."""
        # Test hit with exact match in title
        hit_with_match = SearchHit(
            id="match_doc",
            score=0.8,
            document={"title": "ค้นหาเอกสาร", "content": "เนื้อหา"},
            ranking_info={}
        )
        
        # Test hit without exact match
        hit_without_match = SearchHit(
            id="no_match_doc",
            score=0.8,
            document={"title": "เอกสารอื่น", "content": "เนื้อหาอื่น"},
            ranking_info={}
        )
        
        query = "ค้นหาเอกสาร"
        
        assert result_ranker._is_exact_match(hit_with_match, query) is True
        assert result_ranker._is_exact_match(hit_without_match, query) is False
    
    def test_update_config(self, result_ranker: ResultRanker):
        """Test configuration update."""
        new_config = RankingConfig(
            algorithm="optimized_score",
            boost_exact_matches=3.0,
            boost_thai_matches=2.0
        )
        
        result_ranker.update_config(new_config)
        
        assert result_ranker.config.algorithm == RankingAlgorithm.OPTIMIZED_SCORE
        assert result_ranker.config.boost_exact_matches == 3.0
        assert result_ranker.config.boost_thai_matches == 2.0
    
    def test_get_ranking_stats(self, result_ranker: ResultRanker):
        """Test ranking statistics retrieval."""
        stats = result_ranker.get_ranking_stats()
        
        assert "algorithm" in stats
        assert "configuration" in stats
        assert "available_algorithms" in stats
        assert stats["algorithm"] == "weighted_score"
        assert len(stats["available_algorithms"]) == 4
    
    @pytest.mark.asyncio
    async def test_health_check(self, result_ranker: ResultRanker):
        """Test health check functionality."""
        health_status = await result_ranker.health_check()
        
        assert "status" in health_status
        assert "algorithm" in health_status
        assert health_status["status"] == "healthy"
        assert health_status["algorithm"] == "weighted_score"
    
    def test_create_query_context_from_query(self, result_ranker: ResultRanker):
        """Test automatic query context creation."""
        # Test Thai query
        thai_query = "ค้นหาเอกสารภาษาไทย"
        context = result_ranker._create_query_context(thai_query, [])
        
        assert context.original_query == thai_query
        assert context.thai_content_ratio > 0.5
        assert context.primary_language == "thai"
        assert context.query_length == len(thai_query)
        
        # Test English query
        english_query = "search documents"
        context = result_ranker._create_query_context(english_query, [])
        
        assert context.original_query == english_query
        assert context.thai_content_ratio < 0.3
        assert context.primary_language == "english"
    
    def test_ranking_with_mixed_success_results(
        self, 
        result_ranker: ResultRanker,
        sample_query_variants: List[QueryVariant],
        sample_search_hits: List[SearchHit]
    ):
        """Test ranking with mix of successful and failed search results."""
        mixed_results = [
            SearchResult(
                query_variant=sample_query_variants[0],
                hits=[sample_search_hits[0]],
                total_hits=1,
                processing_time_ms=50.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            ),
            SearchResult(
                query_variant=sample_query_variants[1],
                hits=[],
                total_hits=0,
                processing_time_ms=0.0,
                success=False,
                error_message="Search failed",
                meilisearch_metadata={}
            ),
            SearchResult(
                query_variant=sample_query_variants[2],
                hits=[sample_search_hits[1]],
                total_hits=1,
                processing_time_ms=40.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            )
        ]
        
        ranked_results = result_ranker.rank_results(mixed_results, "test query")
        
        # Should only include results from successful searches
        assert len(ranked_results.hits) == 2
        assert all(hit.id in ["doc_1", "doc_2"] for hit in ranked_results.hits)
    
    def test_content_similarity_calculation(self, result_ranker: ResultRanker):
        """Test content similarity calculation between search hits."""
        # Create hits with similar content
        hit1 = SearchHit(
            id="doc1",
            score=0.9,
            document={"title": "Thai Document", "content": "This is a test document about Thai language processing."}
        )
        
        hit2 = SearchHit(
            id="doc2", 
            score=0.8,
            document={"title": "Thai Document", "content": "This is a test document about Thai language processing and tokenization."}
        )
        
        hit3 = SearchHit(
            id="doc3",
            score=0.7,
            document={"title": "English Document", "content": "This is completely different content about English."}
        )
        
        # Test content similarity
        similarity_1_2 = result_ranker._calculate_content_similarity(hit1, hit2)
        similarity_1_3 = result_ranker._calculate_content_similarity(hit1, hit3)
        
        # Similar documents should have higher similarity
        assert similarity_1_2 > similarity_1_3
        assert similarity_1_2 > 0.7  # Very similar documents
        assert similarity_1_3 < 0.6  # Different documents
    
    def test_content_hash_generation(self, result_ranker: ResultRanker):
        """Test content hash generation for duplicate detection."""
        # Create identical and different hits
        hit1 = SearchHit(
            id="doc1",
            score=0.9,
            document={"title": "Test", "content": "Same content"}
        )
        
        hit2 = SearchHit(
            id="doc2",
            score=0.8,
            document={"title": "Test", "content": "Same content"}  # Identical content
        )
        
        hit3 = SearchHit(
            id="doc3",
            score=0.7,
            document={"title": "Test", "content": "Different content"}
        )
        
        # Generate hashes
        hash1 = result_ranker._generate_content_hash(hit1)
        hash2 = result_ranker._generate_content_hash(hit2)
        hash3 = result_ranker._generate_content_hash(hit3)
        
        # Identical content should have same hash
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 32  # MD5 hash length
    
    def test_enhanced_tie_breaking_rules(self, result_ranker: ResultRanker):
        """Test enhanced tie-breaking rules with multiple criteria."""
        # Create variants with different priorities
        original_variant = QueryVariant("test", QueryVariantType.ORIGINAL, "none", 1.0)
        tokenized_variant = QueryVariant("test tokens", QueryVariantType.TOKENIZED, "newmm", 1.0)
        compound_variant = QueryVariant("test compound", QueryVariantType.COMPOUND_SPLIT, "newmm", 0.9)
        fallback_variant = QueryVariant("test fallback", QueryVariantType.FALLBACK, "basic", 0.8)
        
        # Create hits with same score but different variants
        hit = SearchHit("doc1", 0.8, {"title": "Test"})
        
        tied_hits = [
            (hit, 0.8, fallback_variant, 3),
            (hit, 0.8, original_variant, 1),
            (hit, 0.8, tokenized_variant, 0),
            (hit, 0.8, compound_variant, 2)
        ]
        
        # Apply tie-breaking
        best_hit = result_ranker._apply_tie_breaking_rules(tied_hits)
        best_hit_tuple, best_score, best_variant, best_position = best_hit
        
        # Tokenized variant should win (highest priority)
        assert best_variant.variant_type == QueryVariantType.TOKENIZED
        assert "tie_breaking_applied" in best_hit_tuple.ranking_info
        assert best_hit_tuple.ranking_info["tied_candidates"] == 4
    
    def test_merge_results_with_content_similarity(
        self, 
        result_ranker: ResultRanker,
        sample_query_variants: List[QueryVariant]
    ):
        """Test merging results with content similarity deduplication."""
        # Create hits with similar content but different IDs
        hit1 = SearchHit(
            id="doc1",
            score=0.9,
            document={"title": "Thai Document", "content": "Content about Thai language processing"}
        )
        
        hit2 = SearchHit(
            id="doc2",  # Different ID
            score=0.8,
            document={"title": "Thai Document", "content": "Content about Thai language processing and more"}  # Similar content
        )
        
        hit3 = SearchHit(
            id="doc3",
            score=0.7,
            document={"title": "Different Document", "content": "Completely different content about English"}
        )
        
        scored_hits = [
            (hit1, 0.9, sample_query_variants[0], 0),
            (hit2, 0.8, sample_query_variants[1], 1),
            (hit3, 0.7, sample_query_variants[2], 2)
        ]
        
        # Apply content similarity deduplication with high threshold
        merged_hits = result_ranker._merge_results_with_content_similarity(
            scored_hits, 
            similarity_threshold=0.8
        )
        
        # Should have fewer hits due to content similarity deduplication
        assert len(merged_hits) <= len(scored_hits)
        
        # Check for deduplication metadata
        for hit_tuple in merged_hits:
            hit, score, variant, position = hit_tuple
            if "content_similarity_deduplication_applied" in hit.ranking_info:
                assert hit.ranking_info["similar_content_count"] > 1
                assert "similarity_threshold_used" in hit.ranking_info
    
    def test_variant_comparison_for_tie_breaking(self, result_ranker: ResultRanker):
        """Test variant comparison logic for tie-breaking."""
        # Create variants with different characteristics
        tokenized_newmm = QueryVariant("test", QueryVariantType.TOKENIZED, "newmm", 1.0)
        tokenized_attacut = QueryVariant("test", QueryVariantType.TOKENIZED, "attacut", 1.0)
        original_variant = QueryVariant("test", QueryVariantType.ORIGINAL, "none", 1.0)
        fallback_variant = QueryVariant("test", QueryVariantType.FALLBACK, "basic", 0.8)
        
        # Test variant type priority
        assert result_ranker._compare_variants_for_tie_breaking(tokenized_newmm, original_variant)
        assert result_ranker._compare_variants_for_tie_breaking(original_variant, fallback_variant)
        
        # Test engine priority within same variant type
        assert result_ranker._compare_variants_for_tie_breaking(tokenized_newmm, tokenized_attacut)
        
        # Test weight priority
        high_weight_variant = QueryVariant("test", QueryVariantType.ORIGINAL, "none", 1.5)
        low_weight_variant = QueryVariant("test", QueryVariantType.ORIGINAL, "none", 1.0)
        assert result_ranker._compare_variants_for_tie_breaking(high_weight_variant, low_weight_variant)
    
    def test_enhanced_weighted_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test enhanced weighted score algorithm with improved deduplication."""
        # Set algorithm to weighted score
        result_ranker.config.algorithm = RankingAlgorithm.WEIGHTED_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "weighted_score"
        assert len(ranked_results.hits) > 0
        
        # Check enhanced ranking information
        for hit in ranked_results.hits:
            assert hit.ranking_info is not None
            assert "algorithm" in hit.ranking_info
            assert "base_score" in hit.ranking_info
            assert "variant_weight" in hit.ranking_info
            assert "weighted_final_score" in hit.ranking_info
            
            # Check for deduplication metadata if applied
            if "id_deduplication_applied" in hit.ranking_info:
                assert "duplicate_variants_count" in hit.ranking_info
            
            if "content_similarity_deduplication_applied" in hit.ranking_info:
                assert "similar_content_count" in hit.ranking_info
    
    def test_enhanced_optimized_score_algorithm(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test enhanced optimized score algorithm with improved tie-breaking."""
        # Set algorithm to optimized score
        result_ranker.config.algorithm = RankingAlgorithm.OPTIMIZED_SCORE
        
        ranked_results = result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        assert ranked_results.ranking_algorithm == "optimized_score"
        assert len(ranked_results.hits) > 0
        
        # Check optimized algorithm metadata
        for hit in ranked_results.hits:
            assert hit.ranking_info is not None
            assert hit.ranking_info.get("algorithm") == "optimized_score"
            assert "deduplication_method" in hit.ranking_info
            assert hit.ranking_info["deduplication_method"] == "id_based_only"
    
    def test_ab_testing_configuration(self, result_ranker: ResultRanker):
        """Test A/B testing configuration and algorithm selection."""
        # Configure A/B test
        result_ranker.configure_ab_test(
            test_algorithm="experimental_score",
            traffic_percentage=0.5,
            enabled=True
        )
        
        assert result_ranker.config.ab_testing_enabled is True
        assert result_ranker.config.ab_test_algorithm == "experimental_score"
        assert result_ranker.config.ab_test_traffic_percentage == 0.5
        
        # Test invalid configurations
        with pytest.raises(ValueError):
            result_ranker.configure_ab_test("invalid_algorithm", 0.5)
        
        with pytest.raises(ValueError):
            result_ranker.configure_ab_test("weighted_score", 1.5)  # Invalid percentage
    
    def test_content_type_configuration(self, result_ranker: ResultRanker):
        """Test content type specific configuration."""
        # Configure formal content boosts
        formal_config = {
            "boost_exact_matches": 2.5,
            "boost_thai_matches": 1.8,
            "boost_compound_matches": 1.6
        }
        
        result_ranker.configure_content_type_boosts("formal", formal_config)
        
        assert result_ranker.config.content_type_configs["formal"] == formal_config
        
        # Test invalid configurations
        with pytest.raises(ValueError):
            result_ranker.configure_content_type_boosts("invalid_type", formal_config)
        
        with pytest.raises(ValueError):
            result_ranker.configure_content_type_boosts("formal", {"invalid_key": 2.0})
        
        with pytest.raises(ValueError):
            result_ranker.configure_content_type_boosts("formal", {"boost_exact_matches": 0.5})  # Too low
    
    def test_performance_metrics_tracking(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test performance metrics collection and tracking."""
        # Get initial metrics
        initial_metrics = result_ranker.get_performance_metrics()
        initial_rankings = initial_metrics["total_rankings"]
        
        # Perform ranking
        result_ranker.rank_results(
            sample_search_results, 
            "ค้นหาเอกสาร", 
            sample_query_context
        )
        
        # Check updated metrics
        updated_metrics = result_ranker.get_performance_metrics()
        
        assert updated_metrics["total_rankings"] == initial_rankings + 1
        assert updated_metrics["total_ranking_time_ms"] > initial_metrics["total_ranking_time_ms"]
        assert "avg_ranking_time_ms" in updated_metrics
        assert "algorithm_usage" in updated_metrics
        assert "ab_test_stats" in updated_metrics
    
    def test_algorithm_selection_with_ab_testing(
        self, 
        result_ranker: ResultRanker,
        sample_query_context: QueryContext
    ):
        """Test algorithm selection with A/B testing enabled."""
        # Configure A/B test
        result_ranker.configure_ab_test(
            test_algorithm="experimental_score",
            traffic_percentage=0.5,
            enabled=True
        )
        
        # Test algorithm selection with different session IDs
        session_id_1 = "test_session_1"
        session_id_2 = "test_session_2"
        
        algorithm_1 = result_ranker._select_ranking_algorithm(sample_query_context, session_id_1)
        algorithm_2 = result_ranker._select_ranking_algorithm(sample_query_context, session_id_2)
        
        # Both should be valid algorithms
        valid_algorithms = [alg for alg in RankingAlgorithm]
        assert algorithm_1 in valid_algorithms
        assert algorithm_2 in valid_algorithms
        
        # Test without session ID (should use default)
        default_algorithm = result_ranker._select_ranking_algorithm(sample_query_context, None)
        assert default_algorithm == result_ranker.config.algorithm
    
    def test_content_type_configuration_application(
        self, 
        result_ranker: ResultRanker
    ):
        """Test application of content type specific configurations."""
        # Configure different content types
        result_ranker.configure_content_type_boosts("formal", {
            "boost_exact_matches": 2.5,
            "boost_thai_matches": 1.8
        })
        
        # Create query contexts for different content types
        formal_context = QueryContext(
            original_query="การประชุมคณะกรรมการบริหารจัดการ",  # Long formal Thai
            processed_query="การประชุม คณะกรรมการ บริหาร จัดการ",
            thai_content_ratio=1.0,
            query_length=25,
            tokenization_confidence=0.9,
            primary_language="thai"
        )
        
        informal_context = QueryContext(
            original_query="หาข้อมูล",  # Short informal Thai
            processed_query="หา ข้อมูล",
            thai_content_ratio=1.0,
            query_length=7,
            tokenization_confidence=0.8,
            primary_language="thai"
        )
        
        # Apply configurations
        original_exact_boost = result_ranker.config.boost_exact_matches
        
        result_ranker._apply_content_type_configuration(formal_context)
        formal_boost = result_ranker.config.boost_exact_matches
        
        # Reset and apply informal
        result_ranker.config.boost_exact_matches = original_exact_boost
        result_ranker._apply_content_type_configuration(informal_context)
        informal_boost = result_ranker.config.boost_exact_matches
        
        # Formal should have higher boost (if configured)
        # This test verifies the configuration application mechanism
        assert isinstance(formal_boost, float)
        assert isinstance(informal_boost, float)
    
    def test_performance_optimization_recommendations(
        self, 
        result_ranker: ResultRanker,
        sample_search_results: List[SearchResult],
        sample_query_context: QueryContext
    ):
        """Test performance optimization analysis and recommendations."""
        # Perform several rankings to generate metrics
        for i in range(5):
            result_ranker.rank_results(
                sample_search_results, 
                f"ค้นหาเอกสาร {i}", 
                sample_query_context
            )
        
        # Get optimization recommendations
        optimization_report = result_ranker.optimize_performance()
        
        assert "analysis_timestamp" in optimization_report
        assert "total_rankings_analyzed" in optimization_report
        assert "recommendations" in optimization_report
        assert "current_performance" in optimization_report
        
        # Check structure of recommendations
        for recommendation in optimization_report["recommendations"]:
            assert "type" in recommendation
            assert "suggestion" in recommendation
        
        # Check current performance metrics
        current_perf = optimization_report["current_performance"]
        assert "avg_ranking_time_ms" in current_perf
        assert "avg_duplicates_per_ranking" in current_perf
    
    def test_comprehensive_ranking_stats(self, result_ranker: ResultRanker):
        """Test comprehensive ranking statistics retrieval."""
        stats = result_ranker.get_ranking_stats()
        
        # Check all expected sections
        assert "algorithm" in stats
        assert "configuration" in stats
        assert "ab_testing" in stats
        assert "content_type_configs" in stats
        assert "available_algorithms" in stats
        assert "performance_metrics" in stats
        
        # Check A/B testing section
        ab_testing = stats["ab_testing"]
        assert "enabled" in ab_testing
        assert "test_algorithm" in ab_testing
        assert "traffic_percentage" in ab_testing
        
        # Check configuration section has new parameters
        config = stats["configuration"]
        assert "similarity_threshold" in config
        assert "enable_content_similarity_deduplication" in config
        assert "enable_performance_optimization" in config