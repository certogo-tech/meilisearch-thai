"""
Unit tests for the search proxy ResultRanker component.

Tests result ranking, scoring, merging, and deduplication logic.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.search_proxy.services.result_ranker import (
    ResultRanker, RankedResults, ScoredDocument
)
from src.search_proxy.services.search_executor import SearchResult
from src.search_proxy.config.settings import RankingConfig
from src.search_proxy.models.query import QueryVariant, QueryVariantType
from src.search_proxy.models.search import QueryContext


class TestResultRanker:
    """Test cases for the ResultRanker component."""
    
    @pytest.fixture
    def ranking_config(self):
        """Create test ranking configuration."""
        return RankingConfig(
            algorithm="weighted_score",
            boost_exact_matches=2.0,
            boost_thai_matches=1.5,
            boost_compound_matches=1.3,
            decay_factor=0.1,
            min_score_threshold=0.1,
            max_results_per_variant=100,
            enable_score_normalization=True
        )
    
    @pytest.fixture
    def result_ranker(self, ranking_config):
        """Create a ResultRanker instance for testing."""
        return ResultRanker(ranking_config)
    
    @pytest.fixture
    def query_context(self):
        """Create a test query context."""
        return QueryContext(
            original_query="ค้นหาเอกสาร",
            processed_query="ค้นหา เอกสาร",
            thai_content_ratio=1.0,
            mixed_content=False,
            primary_language="thai",
            query_length=11,
            tokenization_confidence=0.95,
            variant_count=3,
            processing_time_ms=25.0
        )
    
    def create_search_result(self, variant_type, hits, weight=1.0):
        """Helper to create a SearchResult for testing."""
        variant = QueryVariant(
            query_text="test query",
            variant_type=variant_type,
            weight=weight
        )
        
        return SearchResult(
            query_variant=variant,
            index_name="test_index",
            hits=hits,
            total_hits=len(hits),
            search_time_ms=10.0,
            success=True
        )
    
    def test_basic_ranking(self, result_ranker, query_context):
        """Test basic result ranking functionality."""
        # Create search results with different scores
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [
                    {"id": "1", "title": "Document 1", "_rankingScore": 0.9},
                    {"id": "2", "title": "Document 2", "_rankingScore": 0.7}
                ]
            ),
            self.create_search_result(
                QueryVariantType.TOKENIZED,
                [
                    {"id": "3", "title": "Document 3", "_rankingScore": 0.8},
                    {"id": "4", "title": "Document 4", "_rankingScore": 0.6}
                ],
                weight=0.8
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        assert isinstance(ranked_results, RankedResults)
        assert len(ranked_results.hits) == 4
        assert ranked_results.total_unique_hits == 4
        
        # Verify documents are sorted by score
        scores = [hit.final_score for hit in ranked_results.hits]
        assert scores == sorted(scores, reverse=True)
    
    def test_exact_match_boosting(self, result_ranker, query_context):
        """Test that exact matches get boosted scores."""
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,  # Exact match
                [{"id": "1", "title": "Document 1", "_rankingScore": 0.7}]
            ),
            self.create_search_result(
                QueryVariantType.TOKENIZED,  # Not exact
                [{"id": "2", "title": "Document 2", "_rankingScore": 0.7}]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Exact match should rank higher despite same base score
        assert ranked_results.hits[0].document_id == "1"
        assert ranked_results.hits[0].final_score > ranked_results.hits[1].final_score
    
    def test_thai_content_boosting(self, result_ranker):
        """Test that Thai content gets appropriate boosting."""
        # Thai query context
        thai_context = QueryContext(
            original_query="ค้นหาเอกสาร",
            processed_query="ค้นหา เอกสาร",
            thai_content_ratio=1.0,
            mixed_content=False,
            primary_language="thai",
            query_length=11,
            tokenization_confidence=0.95,
            variant_count=2,
            processing_time_ms=20.0
        )
        
        results = [
            self.create_search_result(
                QueryVariantType.TOKENIZED,
                [
                    {"id": "1", "title": "เอกสารภาษาไทย", "_rankingScore": 0.8},
                    {"id": "2", "title": "English Document", "_rankingScore": 0.8}
                ]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="ค้นหาเอกสาร",
            query_context=thai_context
        )
        
        # Both documents should be included
        assert len(ranked_results.hits) == 2
    
    def test_deduplication(self, result_ranker, query_context):
        """Test deduplication of duplicate documents."""
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [
                    {"id": "1", "title": "Document 1", "_rankingScore": 0.9},
                    {"id": "2", "title": "Document 2", "_rankingScore": 0.7}
                ]
            ),
            self.create_search_result(
                QueryVariantType.TOKENIZED,
                [
                    {"id": "1", "title": "Document 1", "_rankingScore": 0.8},  # Duplicate
                    {"id": "3", "title": "Document 3", "_rankingScore": 0.6}
                ]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Should have 3 unique documents
        assert ranked_results.total_unique_hits == 3
        assert ranked_results.deduplication_count == 1
        
        # Document 1 should appear only once with highest score
        doc1_appearances = [hit for hit in ranked_results.hits if hit.document_id == "1"]
        assert len(doc1_appearances) == 1
        assert doc1_appearances[0].final_score >= 0.9  # Should use highest score
    
    def test_score_normalization(self, result_ranker, query_context):
        """Test score normalization across variants."""
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [{"id": "1", "title": "Document 1", "_rankingScore": 0.5}],
                weight=1.0
            ),
            self.create_search_result(
                QueryVariantType.FUZZY,
                [{"id": "2", "title": "Document 2", "_rankingScore": 0.9}],
                weight=0.5  # Lower weight variant
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # All scores should be normalized to [0, 1] range
        for hit in ranked_results.hits:
            assert 0.0 <= hit.final_score <= 1.0
    
    def test_min_score_threshold(self, result_ranker, query_context):
        """Test that documents below minimum score threshold are filtered."""
        result_ranker.config.min_score_threshold = 0.5
        
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [
                    {"id": "1", "title": "High Score", "_rankingScore": 0.8},
                    {"id": "2", "title": "Low Score", "_rankingScore": 0.1}  # Below threshold
                ]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Low score document should be filtered out
        assert len(ranked_results.hits) == 1
        assert ranked_results.hits[0].document_id == "1"
    
    def test_max_results_per_variant(self, result_ranker, query_context):
        """Test limiting results per variant."""
        result_ranker.config.max_results_per_variant = 2
        
        # Create result with many hits
        hits = [{"id": str(i), "title": f"Doc {i}", "_rankingScore": 0.9 - i*0.1} for i in range(5)]
        results = [self.create_search_result(QueryVariantType.ORIGINAL, hits)]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Should only include top 2 results
        assert len(ranked_results.hits) <= 2
    
    def test_empty_results_handling(self, result_ranker, query_context):
        """Test handling of empty search results."""
        results = []
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        assert len(ranked_results.hits) == 0
        assert ranked_results.total_unique_hits == 0
        assert ranked_results.deduplication_count == 0
    
    def test_missing_ranking_score(self, result_ranker, query_context):
        """Test handling of documents without _rankingScore."""
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [
                    {"id": "1", "title": "With Score", "_rankingScore": 0.9},
                    {"id": "2", "title": "Without Score"}  # Missing _rankingScore
                ]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Both documents should be included
        assert len(ranked_results.hits) == 2
        
        # Document without score should get default score
        doc2 = next(hit for hit in ranked_results.hits if hit.document_id == "2")
        assert doc2.base_score == 0.5  # Default score
    
    def test_compound_match_boosting(self, result_ranker, query_context):
        """Test boosting for compound word matches."""
        results = [
            self.create_search_result(
                QueryVariantType.COMPOUND_SPLIT,
                [{"id": "1", "title": "Compound Match", "_rankingScore": 0.7}]
            ),
            self.create_search_result(
                QueryVariantType.TOKENIZED,
                [{"id": "2", "title": "Regular Match", "_rankingScore": 0.7}]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Compound match should rank higher with boost
        compound_hit = next(hit for hit in ranked_results.hits if hit.document_id == "1")
        regular_hit = next(hit for hit in ranked_results.hits if hit.document_id == "2")
        
        assert compound_hit.final_score > regular_hit.final_score
    
    def test_ranking_algorithm_selection(self, result_ranker, query_context):
        """Test different ranking algorithms."""
        # Test with optimized_score algorithm
        result_ranker.config.algorithm = "optimized_score"
        
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [{"id": "1", "title": "Document 1", "_rankingScore": 0.8}]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        assert ranked_results.ranking_algorithm == "optimized_score"
    
    def test_decay_factor_application(self, result_ranker, query_context):
        """Test score decay for lower-ranked results."""
        result_ranker.config.decay_factor = 0.1
        
        # Create many results to test decay
        hits = [
            {"id": str(i), "title": f"Doc {i}", "_rankingScore": 0.8}
            for i in range(10)
        ]
        results = [self.create_search_result(QueryVariantType.ORIGINAL, hits)]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Later results should have progressively lower scores due to decay
        scores = [hit.final_score for hit in ranked_results.hits]
        for i in range(1, len(scores)):
            assert scores[i] <= scores[i-1]
    
    def test_performance_metrics(self, result_ranker, query_context):
        """Test that performance metrics are tracked."""
        results = [
            self.create_search_result(
                QueryVariantType.ORIGINAL,
                [{"id": "1", "title": "Document 1", "_rankingScore": 0.9}]
            )
        ]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        assert ranked_results.ranking_time_ms > 0
        assert isinstance(ranked_results.timestamp, datetime)
    
    def test_failed_search_results_handling(self, result_ranker, query_context):
        """Test handling of failed search results."""
        # Mix of successful and failed results
        successful_result = self.create_search_result(
            QueryVariantType.ORIGINAL,
            [{"id": "1", "title": "Document 1", "_rankingScore": 0.9}]
        )
        
        failed_result = SearchResult(
            query_variant=QueryVariant(
                query_text="failed query",
                variant_type=QueryVariantType.FUZZY,
                weight=0.5
            ),
            index_name="test_index",
            hits=[],
            total_hits=0,
            search_time_ms=0,
            success=False,
            error=Mock()
        )
        
        results = [successful_result, failed_result]
        
        ranked_results = result_ranker.rank_results(
            search_results=results,
            original_query="test query",
            query_context=query_context
        )
        
        # Should only include results from successful searches
        assert len(ranked_results.hits) == 1
        assert ranked_results.hits[0].document_id == "1"