#!/usr/bin/env python3
"""
Comparison script for Thai tokenization search results.

This script compares search results before and after Thai tokenization
to demonstrate the improvement in compound word search accuracy.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

import httpx
from meilisearch import Client as MeiliSearchClient
from meilisearch.errors import MeilisearchError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tokenizer.thai_segmenter import ThaiSegmenter


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result data structure."""
    query: str
    hits: List[Dict[str, Any]]
    total_hits: int
    processing_time_ms: int
    method: str  # 'original' or 'tokenized'


@dataclass
class ComparisonResult:
    """Comparison result between original and tokenized search."""
    query: str
    description: str
    original_result: SearchResult
    tokenized_result: SearchResult
    improvement_score: float
    analysis: str


class SearchComparison:
    """Compare search results with and without Thai tokenization."""
    
    def __init__(self, meilisearch_host: str = "http://localhost:7700",
                 api_key: str = "masterKey"):
        """Initialize comparison tool."""
        self.meilisearch_host = meilisearch_host
        self.api_key = api_key
        self.client = MeiliSearchClient(url=meilisearch_host, api_key=api_key)
        self.tokenizer = ThaiSegmenter()
        self.sample_data_dir = Path(__file__).parent.parent / "data" / "samples"
        
    def setup_comparison_indexes(self) -> Tuple[str, str]:
        """Set up two indexes: one with original text, one with tokenized text."""
        original_index = "thai_original"
        tokenized_index = "thai_tokenized"
        
        # Load sample documents
        documents = self.load_sample_documents()
        
        # Create original index (no tokenization)
        self.create_original_index(documents, original_index)
        
        # Create tokenized index (with Thai tokenization)
        self.create_tokenized_index(documents, tokenized_index)
        
        return original_index, tokenized_index
    
    def load_sample_documents(self) -> List[Dict[str, Any]]:
        """Load sample documents for comparison."""
        all_documents = []
        
        document_files = [
            "thai_documents.json",
            "formal_documents.json",
            "informal_documents.json"
        ]
        
        for filename in document_files:
            file_path = self.sample_data_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                    all_documents.extend(documents)
        
        return all_documents
    
    def create_original_index(self, documents: List[Dict[str, Any]], 
                            index_name: str) -> None:
        """Create index with original (non-tokenized) Thai text."""
        try:
            # Delete existing index if it exists
            try:
                self.client.delete_index(index_name)
                time.sleep(1)  # Wait for deletion
            except:
                pass
            
            # Create new index
            index = self.client.create_index(index_name, {'primaryKey': 'id'})
            
            # Configure basic settings
            index.update_searchable_attributes(['title', 'content', 'tags'])
            index.update_filterable_attributes(['category'])
            
            # Add documents without tokenization
            original_docs = []
            for doc in documents:
                original_doc = {
                    'id': doc['id'],
                    'title': doc.get('title', ''),
                    'content': doc.get('content', ''),
                    'category': doc.get('category', 'general'),
                    'tags': doc.get('tags', [])
                }
                original_docs.append(original_doc)
            
            # Add to index
            task = index.add_documents(original_docs)
            self.client.wait_for_task(task.task_uid)
            
            logger.info(f"Created original index '{index_name}' with {len(original_docs)} documents")
            
        except Exception as e:
            logger.error(f"Error creating original index: {e}")
            raise
    
    def create_tokenized_index(self, documents: List[Dict[str, Any]], 
                             index_name: str) -> None:
        """Create index with Thai-tokenized text."""
        try:
            # Delete existing index if it exists
            try:
                self.client.delete_index(index_name)
                time.sleep(1)  # Wait for deletion
            except:
                pass
            
            # Create new index
            index = self.client.create_index(index_name, {'primaryKey': 'id'})
            
            # Configure enhanced settings for tokenized content
            searchable_attributes = [
                'title', 'content', 'title_tokenized', 'content_tokenized',
                'searchable_text_tokenized', 'tags'
            ]
            index.update_searchable_attributes(searchable_attributes)
            index.update_filterable_attributes(['category'])
            
            # Process documents with tokenization
            tokenized_docs = []
            for doc in documents:
                # Tokenize Thai content
                title_tokens = self.tokenizer.tokenize(doc.get('title', ''))
                content_tokens = self.tokenizer.tokenize(doc.get('content', ''))
                
                tokenized_doc = {
                    'id': doc['id'],
                    'title': doc.get('title', ''),
                    'content': doc.get('content', ''),
                    'title_tokenized': ' '.join(title_tokens),
                    'content_tokenized': ' '.join(content_tokens),
                    'searchable_text_tokenized': ' '.join(title_tokens + content_tokens),
                    'category': doc.get('category', 'general'),
                    'tags': doc.get('tags', [])
                }
                tokenized_docs.append(tokenized_doc)
            
            # Add to index
            task = index.add_documents(tokenized_docs)
            self.client.wait_for_task(task.task_uid)
            
            logger.info(f"Created tokenized index '{index_name}' with {len(tokenized_docs)} documents")
            
        except Exception as e:
            logger.error(f"Error creating tokenized index: {e}")
            raise
    
    def search_index(self, index_name: str, query: str, method: str) -> SearchResult:
        """Search an index and return structured results."""
        try:
            index = self.client.index(index_name)
            
            search_params = {
                'limit': 10,
                'attributesToHighlight': ['title', 'content', 'title_tokenized', 'content_tokenized'],
                'highlightPreTag': '<mark>',
                'highlightPostTag': '</mark>'
            }
            
            start_time = time.time()
            results = index.search(query, search_params)
            processing_time = int((time.time() - start_time) * 1000)
            
            return SearchResult(
                query=query,
                hits=results['hits'],
                total_hits=results['estimatedTotalHits'],
                processing_time_ms=processing_time,
                method=method
            )
            
        except Exception as e:
            logger.error(f"Error searching index {index_name}: {e}")
            return SearchResult(query, [], 0, 0, method)
    
    def calculate_improvement_score(self, original: SearchResult, 
                                  tokenized: SearchResult,
                                  expected_results: List[str] = None) -> float:
        """Calculate improvement score between original and tokenized results."""
        score = 0.0
        
        # Factor 1: Number of results (more results can be better for compound words)
        if tokenized.total_hits > original.total_hits:
            score += 0.3
        elif tokenized.total_hits == original.total_hits and tokenized.total_hits > 0:
            score += 0.1
        
        # Factor 2: Relevance of top results (check if expected results are in top positions)
        if expected_results:
            original_top_ids = [hit['id'] for hit in original.hits[:3]]
            tokenized_top_ids = [hit['id'] for hit in tokenized.hits[:3]]
            
            original_matches = len(set(expected_results) & set(original_top_ids))
            tokenized_matches = len(set(expected_results) & set(tokenized_top_ids))
            
            if tokenized_matches > original_matches:
                score += 0.4
            elif tokenized_matches == original_matches and tokenized_matches > 0:
                score += 0.2
        
        # Factor 3: Performance (faster is better, but not as important)
        if tokenized.processing_time_ms <= original.processing_time_ms:
            score += 0.1
        
        # Factor 4: Quality of highlighting (more highlights suggest better matching)
        original_highlights = sum(1 for hit in original.hits for field in hit.get('_formatted', {}).values() 
                                if isinstance(field, str) and '<mark>' in field)
        tokenized_highlights = sum(1 for hit in tokenized.hits for field in hit.get('_formatted', {}).values() 
                                 if isinstance(field, str) and '<mark>' in field)
        
        if tokenized_highlights > original_highlights:
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def analyze_results(self, original: SearchResult, tokenized: SearchResult,
                       expected_results: List[str] = None) -> str:
        """Analyze and describe the differences between results."""
        analysis = []
        
        # Results count analysis
        if tokenized.total_hits > original.total_hits:
            analysis.append(f"✓ Tokenized search found {tokenized.total_hits - original.total_hits} more results")
        elif tokenized.total_hits < original.total_hits:
            analysis.append(f"⚠ Tokenized search found {original.total_hits - tokenized.total_hits} fewer results")
        else:
            analysis.append(f"= Same number of results ({tokenized.total_hits})")
        
        # Performance analysis
        if tokenized.processing_time_ms < original.processing_time_ms:
            improvement = original.processing_time_ms - tokenized.processing_time_ms
            analysis.append(f"✓ {improvement}ms faster processing")
        elif tokenized.processing_time_ms > original.processing_time_ms:
            slower = tokenized.processing_time_ms - original.processing_time_ms
            analysis.append(f"⚠ {slower}ms slower processing")
        
        # Relevance analysis
        if expected_results:
            original_top_ids = [hit['id'] for hit in original.hits[:3]]
            tokenized_top_ids = [hit['id'] for hit in tokenized.hits[:3]]
            
            original_matches = len(set(expected_results) & set(original_top_ids))
            tokenized_matches = len(set(expected_results) & set(tokenized_top_ids))
            
            if tokenized_matches > original_matches:
                analysis.append(f"✓ Better relevance: {tokenized_matches}/{len(expected_results)} expected results in top 3")
            elif tokenized_matches < original_matches:
                analysis.append(f"⚠ Lower relevance: {tokenized_matches}/{len(expected_results)} expected results in top 3")
            else:
                analysis.append(f"= Same relevance: {tokenized_matches}/{len(expected_results)} expected results in top 3")
        
        return " | ".join(analysis) if analysis else "No significant differences"
    
    def run_comparison(self, test_queries: List[Dict[str, Any]], 
                      original_index: str, tokenized_index: str) -> List[ComparisonResult]:
        """Run comparison tests on both indexes."""
        results = []
        
        for query_data in test_queries:
            query = query_data['query']
            description = query_data['description']
            expected_results = query_data.get('expected_results', [])
            
            logger.info(f"Testing query: '{query}'")
            
            # Search both indexes
            original_result = self.search_index(original_index, query, 'original')
            tokenized_result = self.search_index(tokenized_index, query, 'tokenized')
            
            # Calculate improvement
            improvement_score = self.calculate_improvement_score(
                original_result, tokenized_result, expected_results
            )
            
            # Analyze results
            analysis = self.analyze_results(
                original_result, tokenized_result, expected_results
            )
            
            comparison = ComparisonResult(
                query=query,
                description=description,
                original_result=original_result,
                tokenized_result=tokenized_result,
                improvement_score=improvement_score,
                analysis=analysis
            )
            
            results.append(comparison)
        
        return results
    
    def print_comparison_report(self, comparisons: List[ComparisonResult]) -> None:
        """Print detailed comparison report."""
        print("\n" + "=" * 80)
        print("THAI TOKENIZATION SEARCH COMPARISON REPORT")
        print("=" * 80)
        
        total_queries = len(comparisons)
        improved_queries = sum(1 for c in comparisons if c.improvement_score > 0.5)
        avg_improvement = sum(c.improvement_score for c in comparisons) / total_queries
        
        print(f"\nSUMMARY:")
        print(f"Total queries tested: {total_queries}")
        print(f"Queries with improvement: {improved_queries} ({improved_queries/total_queries*100:.1f}%)")
        print(f"Average improvement score: {avg_improvement:.3f}")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 80)
        
        for i, comp in enumerate(comparisons, 1):
            print(f"\n{i}. Query: '{comp.query}'")
            print(f"   Description: {comp.description}")
            print(f"   Improvement Score: {comp.improvement_score:.3f}")
            print(f"   Analysis: {comp.analysis}")
            
            print(f"   Original Results: {comp.original_result.total_hits} hits in {comp.original_result.processing_time_ms}ms")
            for j, hit in enumerate(comp.original_result.hits[:3], 1):
                print(f"     {j}. {hit['title']} (ID: {hit['id']})")
            
            print(f"   Tokenized Results: {comp.tokenized_result.total_hits} hits in {comp.tokenized_result.processing_time_ms}ms")
            for j, hit in enumerate(comp.tokenized_result.hits[:3], 1):
                print(f"     {j}. {hit['title']} (ID: {hit['id']})")
        
        print("\n" + "=" * 80)
    
    def save_comparison_report(self, comparisons: List[ComparisonResult], 
                             output_file: str = "comparison_report.json") -> None:
        """Save comparison results to JSON file."""
        report_data = {
            'timestamp': int(time.time()),
            'summary': {
                'total_queries': len(comparisons),
                'improved_queries': sum(1 for c in comparisons if c.improvement_score > 0.5),
                'average_improvement': sum(c.improvement_score for c in comparisons) / len(comparisons)
            },
            'comparisons': []
        }
        
        for comp in comparisons:
            comp_data = {
                'query': comp.query,
                'description': comp.description,
                'improvement_score': comp.improvement_score,
                'analysis': comp.analysis,
                'original_results': {
                    'total_hits': comp.original_result.total_hits,
                    'processing_time_ms': comp.original_result.processing_time_ms,
                    'top_hits': [{'id': hit['id'], 'title': hit['title']} 
                               for hit in comp.original_result.hits[:5]]
                },
                'tokenized_results': {
                    'total_hits': comp.tokenized_result.total_hits,
                    'processing_time_ms': comp.tokenized_result.processing_time_ms,
                    'top_hits': [{'id': hit['id'], 'title': hit['title']} 
                               for hit in comp.tokenized_result.hits[:5]]
                }
            }
            report_data['comparisons'].append(comp_data)
        
        output_path = Path(__file__).parent.parent / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Comparison report saved to {output_path}")
    
    async def run_full_comparison(self) -> None:
        """Run the complete comparison analysis."""
        logger.info("Starting Thai Tokenization Comparison")
        logger.info("=" * 50)
        
        try:
            # Set up comparison indexes
            logger.info("Setting up comparison indexes...")
            original_index, tokenized_index = self.setup_comparison_indexes()
            
            # Load test queries
            queries_file = self.sample_data_dir / "test_queries.json"
            with open(queries_file, 'r', encoding='utf-8') as f:
                test_queries = json.load(f)
            
            # Run comparison
            logger.info(f"Running comparison with {len(test_queries)} test queries...")
            comparisons = self.run_comparison(test_queries, original_index, tokenized_index)
            
            # Print report
            self.print_comparison_report(comparisons)
            
            # Save report
            self.save_comparison_report(comparisons)
            
            logger.info("Comparison completed successfully!")
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            raise


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare Thai tokenization search results")
    parser.add_argument("--host", default="http://localhost:7700",
                       help="MeiliSearch host URL")
    parser.add_argument("--api-key", default="masterKey",
                       help="MeiliSearch API key")
    
    args = parser.parse_args()
    
    comparison = SearchComparison(meilisearch_host=args.host, api_key=args.api_key)
    await comparison.run_full_comparison()


if __name__ == "__main__":
    asyncio.run(main())