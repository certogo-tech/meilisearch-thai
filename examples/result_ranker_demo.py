#!/usr/bin/env python3
"""
Demo script for the ResultRanker class.

This script demonstrates how to use the ResultRanker to rank and score
search results from multiple query variants.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from search_proxy.services.result_ranker import ResultRanker, RankingAlgorithm
from search_proxy.config.settings import RankingConfig
from search_proxy.models.search import SearchResult, QueryContext
from search_proxy.models.responses import SearchHit
from search_proxy.models.query import QueryVariant, QueryVariantType


def create_sample_data():
    """Create sample search results for demonstration."""
    
    # Create sample query variants
    query_variants = [
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
    
    # Create sample search hits
    sample_hits = [
        SearchHit(
            id="doc_1",
            score=0.95,
            document={
                "title": "คู่มือการค้นหาเอกสาร",
                "content": "วิธีการค้นหาเอกสารในระบบ",
                "language": "thai"
            },
            highlight={"title": ["คู่มือการ<em>ค้นหาเอกสาร</em>"]},
            ranking_info={"base_score": 0.95}
        ),
        SearchHit(
            id="doc_2",
            score=0.85,
            document={
                "title": "เอกสารสำคัญ",
                "content": "เอกสารที่ต้องการค้นหา",
                "language": "thai"
            },
            highlight={"content": ["<em>เอกสาร</em>ที่ต้องการ<em>ค้นหา</em>"]},
            ranking_info={"base_score": 0.85}
        ),
        SearchHit(
            id="doc_3",
            score=0.75,
            document={
                "title": "Document Search Guide",
                "content": "How to search for documents",
                "language": "english"
            },
            highlight={"title": ["<em>Document Search</em> Guide"]},
            ranking_info={"base_score": 0.75}
        ),
        SearchHit(
            id="doc_4",
            score=0.80,
            document={
                "title": "การจัดเก็บเอกสาร",
                "content": "วิธีการจัดเก็บและค้นหาเอกสาร",
                "language": "thai"
            },
            highlight={"content": ["วิธีการจัดเก็บและ<em>ค้นหาเอกสาร</em>"]},
            ranking_info={"base_score": 0.80}
        )
    ]
    
    # Create search results from different variants
    search_results = [
        SearchResult(
            query_variant=query_variants[0],
            hits=[sample_hits[0], sample_hits[1]],
            total_hits=2,
            processing_time_ms=45.0,
            success=True,
            error_message=None,
            meilisearch_metadata={"processingTimeMs": 40}
        ),
        SearchResult(
            query_variant=query_variants[1],
            hits=[sample_hits[0], sample_hits[2], sample_hits[3]],
            total_hits=3,
            processing_time_ms=55.0,
            success=True,
            error_message=None,
            meilisearch_metadata={"processingTimeMs": 50}
        ),
        SearchResult(
            query_variant=query_variants[2],
            hits=[sample_hits[1], sample_hits[3]],
            total_hits=2,
            processing_time_ms=35.0,
            success=True,
            error_message=None,
            meilisearch_metadata={"processingTimeMs": 30}
        )
    ]
    
    # Create query context
    query_context = QueryContext(
        original_query="ค้นหาเอกสาร",
        processed_query="ค้นหา เอกสาร",
        thai_content_ratio=1.0,
        query_length=10,
        tokenization_confidence=0.9,
        primary_language="thai"
    )
    
    return search_results, query_context


def demonstrate_ranking_algorithms():
    """Demonstrate different ranking algorithms."""
    
    print("=== ResultRanker Demo ===\n")
    
    # Create sample data
    search_results, query_context = create_sample_data()
    
    print(f"Original query: {query_context.original_query}")
    print(f"Thai content ratio: {query_context.thai_content_ratio}")
    print(f"Query variants: {len(search_results)}")
    print(f"Total raw hits: {sum(len(r.hits) for r in search_results)}")
    print()
    
    # Test different ranking algorithms
    algorithms = [
        ("weighted_score", "Weighted Score Algorithm"),
        ("optimized_score", "Optimized Score Algorithm"),
        ("simple_score", "Simple Score Algorithm"),
        ("experimental_score", "Experimental Score Algorithm")
    ]
    
    for algorithm_name, algorithm_title in algorithms:
        print(f"--- {algorithm_title} ---")
        
        # Create ranking configuration
        config = RankingConfig(
            algorithm=algorithm_name,
            boost_exact_matches=2.0,
            boost_thai_matches=1.5,
            boost_compound_matches=1.3,
            min_score_threshold=0.1,
            enable_score_normalization=True
        )
        
        # Create ranker
        ranker = ResultRanker(config)
        
        # Rank results
        ranked_results = ranker.rank_results(
            search_results, 
            query_context.original_query, 
            query_context
        )
        
        print(f"Algorithm: {ranked_results.ranking_algorithm}")
        print(f"Unique hits: {ranked_results.total_unique_hits}")
        print(f"Deduplication count: {ranked_results.deduplication_count}")
        print(f"Ranking time: {ranked_results.ranking_time_ms:.2f}ms")
        print()
        
        # Show top results
        print("Top results:")
        for i, hit in enumerate(ranked_results.hits[:3], 1):
            title = hit.document.get("title", "No title")
            language = hit.document.get("language", "unknown")
            print(f"  {i}. {title} (score: {hit.score:.3f}, lang: {language})")
            
            if hit.ranking_info:
                variant_type = hit.ranking_info.get("variant_type", "unknown")
                print(f"     Variant: {variant_type}")
        
        print()


def demonstrate_configuration_options():
    """Demonstrate different configuration options."""
    
    print("=== Configuration Options Demo ===\n")
    
    search_results, query_context = create_sample_data()
    
    # Test different boost configurations
    configurations = [
        {
            "name": "High Thai Boost",
            "config": RankingConfig(
                algorithm="weighted_score",
                boost_exact_matches=1.5,
                boost_thai_matches=2.5,
                boost_compound_matches=1.2
            )
        },
        {
            "name": "High Exact Match Boost",
            "config": RankingConfig(
                algorithm="weighted_score",
                boost_exact_matches=3.0,
                boost_thai_matches=1.2,
                boost_compound_matches=1.1
            )
        },
        {
            "name": "Balanced Boost",
            "config": RankingConfig(
                algorithm="weighted_score",
                boost_exact_matches=1.8,
                boost_thai_matches=1.8,
                boost_compound_matches=1.5
            )
        }
    ]
    
    for config_info in configurations:
        print(f"--- {config_info['name']} ---")
        
        ranker = ResultRanker(config_info['config'])
        ranked_results = ranker.rank_results(
            search_results, 
            query_context.original_query, 
            query_context
        )
        
        print("Top 3 results:")
        for i, hit in enumerate(ranked_results.hits[:3], 1):
            title = hit.document.get("title", "No title")
            print(f"  {i}. {title} (score: {hit.score:.3f})")
        
        print()


async def demonstrate_health_check():
    """Demonstrate health check functionality."""
    
    print("=== Health Check Demo ===\n")
    
    config = RankingConfig(algorithm="weighted_score")
    ranker = ResultRanker(config)
    
    # Perform health check
    health_status = await ranker.health_check()
    
    print("Health Check Results:")
    print(f"Status: {health_status['status']}")
    print(f"Algorithm: {health_status['algorithm']}")
    print(f"Configuration Valid: {health_status.get('configuration_valid', 'unknown')}")
    
    if health_status['status'] == 'healthy':
        print("✅ ResultRanker is healthy and ready to use")
    else:
        print("❌ ResultRanker has health issues")
        if 'error' in health_status:
            print(f"Error: {health_status['error']}")
    
    print()


def main():
    """Main demo function."""
    
    try:
        # Demonstrate ranking algorithms
        demonstrate_ranking_algorithms()
        
        # Demonstrate configuration options
        demonstrate_configuration_options()
        
        # Demonstrate health check
        import asyncio
        asyncio.run(demonstrate_health_check())
        
        print("=== Demo Complete ===")
        print("The ResultRanker successfully ranked search results using different algorithms")
        print("and configuration options, demonstrating Thai language-aware scoring.")
        
    except Exception as e:
        print(f"Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())