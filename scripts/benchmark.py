#!/usr/bin/env python3
"""
Performance benchmark script for Thai tokenizer and MeiliSearch integration.

This script measures tokenization speed, indexing performance, and search
response times to validate performance requirements.
"""

import asyncio
import json
import logging
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

import httpx
import psutil
from meilisearch import Client as MeiliSearchClient

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
class BenchmarkResult:
    """Benchmark result data structure."""
    test_name: str
    total_operations: int
    total_time_seconds: float
    operations_per_second: float
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    memory_usage_mb: float
    success_rate: float


class PerformanceBenchmark:
    """Performance benchmarking for Thai tokenizer system."""
    
    def __init__(self, meilisearch_host: str = "http://localhost:7700",
                 api_key: str = "masterKey",
                 tokenizer_host: str = "http://localhost:8000"):
        """Initialize benchmark suite."""
        self.meilisearch_host = meilisearch_host
        self.api_key = api_key
        self.tokenizer_host = tokenizer_host
        self.client = MeiliSearchClient(url=meilisearch_host, api_key=api_key)
        self.tokenizer = ThaiSegmenter()
        self.sample_data_dir = Path(__file__).parent.parent / "sample_data"
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def load_test_data(self) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Load test data for benchmarking."""
        # Load documents
        documents = []
        document_files = [
            "thai_documents.json",
            "formal_documents.json",
            "informal_documents.json"
        ]
        
        for filename in document_files:
            file_path = self.sample_data_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    docs = json.load(f)
                    documents.extend(docs)
        
        # Extract text samples for tokenization testing
        text_samples = []
        for doc in documents:
            text_samples.append(doc.get('title', ''))
            text_samples.append(doc.get('content', ''))
        
        # Filter out empty strings and create various length samples
        text_samples = [text for text in text_samples if text.strip()]
        
        # Create samples of different lengths for comprehensive testing
        short_texts = [text for text in text_samples if len(text) < 100]
        medium_texts = [text for text in text_samples if 100 <= len(text) < 500]
        long_texts = [text for text in text_samples if len(text) >= 500]
        
        # Combine for balanced testing
        balanced_samples = short_texts[:10] + medium_texts[:10] + long_texts[:10]
        
        return balanced_samples, documents
    
    def benchmark_tokenization(self, text_samples: List[str], 
                             iterations: int = 100) -> BenchmarkResult:
        """Benchmark Thai tokenization performance."""
        logger.info(f"Benchmarking tokenization with {len(text_samples)} samples, {iterations} iterations")
        
        times = []
        successes = 0
        start_memory = self.get_memory_usage()
        
        start_time = time.time()
        
        for i in range(iterations):
            for text in text_samples:
                try:
                    operation_start = time.time()
                    tokens = self.tokenizer.tokenize(text)
                    operation_time = (time.time() - operation_start) * 1000  # Convert to ms
                    
                    times.append(operation_time)
                    successes += 1
                    
                except Exception as e:
                    logger.warning(f"Tokenization failed for iteration {i}: {e}")
        
        total_time = time.time() - start_time
        end_memory = self.get_memory_usage()
        
        total_operations = len(text_samples) * iterations
        
        return BenchmarkResult(
            test_name="Thai Tokenization",
            total_operations=total_operations,
            total_time_seconds=total_time,
            operations_per_second=total_operations / total_time,
            average_time_ms=statistics.mean(times) if times else 0,
            min_time_ms=min(times) if times else 0,
            max_time_ms=max(times) if times else 0,
            median_time_ms=statistics.median(times) if times else 0,
            p95_time_ms=statistics.quantiles(times, n=20)[18] if len(times) > 20 else (max(times) if times else 0),
            memory_usage_mb=end_memory - start_memory,
            success_rate=successes / total_operations if total_operations > 0 else 0
        )
    
    async def benchmark_api_tokenization(self, text_samples: List[str],
                                       concurrent_requests: int = 10) -> BenchmarkResult:
        """Benchmark tokenization API performance."""
        logger.info(f"Benchmarking API tokenization with {len(text_samples)} samples, {concurrent_requests} concurrent requests")
        
        times = []
        successes = 0
        start_memory = self.get_memory_usage()
        
        async def tokenize_request(session: httpx.AsyncClient, text: str) -> float:
            """Single tokenization request."""
            try:
                start_time = time.time()
                response = await session.post(
                    f"{self.tokenizer_host}/api/v1/tokenize",
                    json={"text": text},
                    timeout=30.0
                )
                request_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    return request_time
                else:
                    logger.warning(f"API request failed with status {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.warning(f"API request failed: {e}")
                return None
        
        start_time = time.time()
        
        async with httpx.AsyncClient() as session:
            # Create tasks for concurrent requests
            tasks = []
            for text in text_samples:
                for _ in range(concurrent_requests):
                    tasks.append(tokenize_request(session, text))
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, (int, float)) and result is not None:
                    times.append(result)
                    successes += 1
        
        total_time = time.time() - start_time
        end_memory = self.get_memory_usage()
        
        total_operations = len(text_samples) * concurrent_requests
        
        return BenchmarkResult(
            test_name="API Tokenization",
            total_operations=total_operations,
            total_time_seconds=total_time,
            operations_per_second=total_operations / total_time,
            average_time_ms=statistics.mean(times) if times else 0,
            min_time_ms=min(times) if times else 0,
            max_time_ms=max(times) if times else 0,
            median_time_ms=statistics.median(times) if times else 0,
            p95_time_ms=statistics.quantiles(times, n=20)[18] if len(times) > 20 else (max(times) if times else 0),
            memory_usage_mb=end_memory - start_memory,
            success_rate=successes / total_operations if total_operations > 0 else 0
        )
    
    def benchmark_indexing(self, documents: List[Dict[str, Any]],
                          batch_size: int = 10) -> BenchmarkResult:
        """Benchmark document indexing performance."""
        logger.info(f"Benchmarking indexing with {len(documents)} documents, batch size {batch_size}")
        
        index_name = "benchmark_index"
        
        # Clean up existing index
        try:
            self.client.delete_index(index_name)
            time.sleep(1)
        except:
            pass
        
        # Create new index
        index = self.client.create_index(index_name, {'primaryKey': 'id'})
        
        times = []
        successes = 0
        start_memory = self.get_memory_usage()
        
        # Preprocess documents with tokenization
        processed_docs = []
        for doc in documents:
            title_tokens = self.tokenizer.tokenize(doc.get('title', ''))
            content_tokens = self.tokenizer.tokenize(doc.get('content', ''))
            
            processed_doc = {
                'id': f"bench_{doc['id']}",
                'title': doc.get('title', ''),
                'content': doc.get('content', ''),
                'title_tokenized': ' '.join(title_tokens),
                'content_tokenized': ' '.join(content_tokens),
                'category': doc.get('category', 'general')
            }
            processed_docs.append(processed_doc)
        
        start_time = time.time()
        
        # Index documents in batches
        for i in range(0, len(processed_docs), batch_size):
            batch = processed_docs[i:i + batch_size]
            
            try:
                batch_start = time.time()
                task = index.add_documents(batch)
                self.client.wait_for_task(task.task_uid)
                batch_time = (time.time() - batch_start) * 1000
                
                times.append(batch_time)
                successes += len(batch)
                
            except Exception as e:
                logger.warning(f"Indexing batch failed: {e}")
        
        total_time = time.time() - start_time
        end_memory = self.get_memory_usage()
        
        # Clean up
        try:
            self.client.delete_index(index_name)
        except:
            pass
        
        return BenchmarkResult(
            test_name="Document Indexing",
            total_operations=len(processed_docs),
            total_time_seconds=total_time,
            operations_per_second=len(processed_docs) / total_time,
            average_time_ms=statistics.mean(times) if times else 0,
            min_time_ms=min(times) if times else 0,
            max_time_ms=max(times) if times else 0,
            median_time_ms=statistics.median(times) if times else 0,
            p95_time_ms=statistics.quantiles(times, n=20)[18] if len(times) > 20 else (max(times) if times else 0),
            memory_usage_mb=end_memory - start_memory,
            success_rate=successes / len(processed_docs) if processed_docs else 0
        )
    
    def benchmark_search(self, queries: List[str], index_name: str = "thai_documents",
                        iterations: int = 50) -> BenchmarkResult:
        """Benchmark search performance."""
        logger.info(f"Benchmarking search with {len(queries)} queries, {iterations} iterations")
        
        index = self.client.index(index_name)
        times = []
        successes = 0
        start_memory = self.get_memory_usage()
        
        start_time = time.time()
        
        for i in range(iterations):
            for query in queries:
                try:
                    query_start = time.time()
                    results = index.search(query, {'limit': 10})
                    query_time = (time.time() - query_start) * 1000
                    
                    times.append(query_time)
                    successes += 1
                    
                except Exception as e:
                    logger.warning(f"Search failed for query '{query}': {e}")
        
        total_time = time.time() - start_time
        end_memory = self.get_memory_usage()
        
        total_operations = len(queries) * iterations
        
        return BenchmarkResult(
            test_name="Search Performance",
            total_operations=total_operations,
            total_time_seconds=total_time,
            operations_per_second=total_operations / total_time,
            average_time_ms=statistics.mean(times) if times else 0,
            min_time_ms=min(times) if times else 0,
            max_time_ms=max(times) if times else 0,
            median_time_ms=statistics.median(times) if times else 0,
            p95_time_ms=statistics.quantiles(times, n=20)[18] if len(times) > 20 else (max(times) if times else 0),
            memory_usage_mb=end_memory - start_memory,
            success_rate=successes / total_operations if total_operations > 0 else 0
        )
    
    def print_benchmark_report(self, results: List[BenchmarkResult]) -> None:
        """Print detailed benchmark report."""
        print("\n" + "=" * 80)
        print("THAI TOKENIZER PERFORMANCE BENCHMARK REPORT")
        print("=" * 80)
        
        for result in results:
            print(f"\n{result.test_name.upper()}")
            print("-" * 40)
            print(f"Total Operations: {result.total_operations:,}")
            print(f"Total Time: {result.total_time_seconds:.2f}s")
            print(f"Operations/Second: {result.operations_per_second:.2f}")
            print(f"Success Rate: {result.success_rate:.1%}")
            print(f"Memory Usage: {result.memory_usage_mb:+.2f} MB")
            print(f"\nTiming Statistics (ms):")
            print(f"  Average: {result.average_time_ms:.2f}")
            print(f"  Median:  {result.median_time_ms:.2f}")
            print(f"  Min:     {result.min_time_ms:.2f}")
            print(f"  Max:     {result.max_time_ms:.2f}")
            print(f"  95th %:  {result.p95_time_ms:.2f}")
            
            # Performance assessment
            self.assess_performance(result)
        
        print("\n" + "=" * 80)
    
    def assess_performance(self, result: BenchmarkResult) -> None:
        """Assess performance against requirements."""
        print(f"\nPerformance Assessment:")
        
        if result.test_name == "Thai Tokenization":
            # Target: < 50ms for 1000 characters
            if result.average_time_ms < 50:
                print("  ✓ Tokenization speed meets requirements")
            else:
                print(f"  ⚠ Tokenization speed ({result.average_time_ms:.2f}ms) exceeds 50ms target")
        
        elif result.test_name == "Search Performance":
            # Target: < 100ms for typical queries
            if result.average_time_ms < 100:
                print("  ✓ Search response time meets requirements")
            else:
                print(f"  ⚠ Search response time ({result.average_time_ms:.2f}ms) exceeds 100ms target")
        
        elif result.test_name == "Document Indexing":
            # Target: > 500 documents/second
            if result.operations_per_second > 500:
                print("  ✓ Indexing throughput meets requirements")
            else:
                print(f"  ⚠ Indexing throughput ({result.operations_per_second:.2f}/s) below 500/s target")
        
        # Memory usage assessment
        if result.memory_usage_mb < 256:
            print("  ✓ Memory usage within limits")
        else:
            print(f"  ⚠ Memory usage ({result.memory_usage_mb:.2f}MB) exceeds 256MB target")
        
        # Success rate assessment
        if result.success_rate > 0.99:
            print("  ✓ Excellent reliability")
        elif result.success_rate > 0.95:
            print("  ✓ Good reliability")
        else:
            print(f"  ⚠ Low reliability ({result.success_rate:.1%})")
    
    def save_benchmark_report(self, results: List[BenchmarkResult],
                            output_file: str = "benchmark_report.json") -> None:
        """Save benchmark results to JSON file."""
        report_data = {
            'timestamp': int(time.time()),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                'python_version': sys.version
            },
            'results': []
        }
        
        for result in results:
            result_data = {
                'test_name': result.test_name,
                'total_operations': result.total_operations,
                'total_time_seconds': result.total_time_seconds,
                'operations_per_second': result.operations_per_second,
                'average_time_ms': result.average_time_ms,
                'min_time_ms': result.min_time_ms,
                'max_time_ms': result.max_time_ms,
                'median_time_ms': result.median_time_ms,
                'p95_time_ms': result.p95_time_ms,
                'memory_usage_mb': result.memory_usage_mb,
                'success_rate': result.success_rate
            }
            report_data['results'].append(result_data)
        
        output_path = Path(__file__).parent.parent / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"Benchmark report saved to {output_path}")
    
    async def run_full_benchmark(self) -> None:
        """Run complete performance benchmark suite."""
        logger.info("Starting Thai Tokenizer Performance Benchmark")
        logger.info("=" * 50)
        
        try:
            # Load test data
            logger.info("Loading test data...")
            text_samples, documents = self.load_test_data()
            
            # Load test queries
            queries_file = self.sample_data_dir / "test_queries.json"
            if queries_file.exists():
                with open(queries_file, 'r', encoding='utf-8') as f:
                    query_data = json.load(f)
                    queries = [q['query'] for q in query_data[:10]]  # Use first 10 queries
            else:
                queries = ["ปัญญาประดิษฐ์", "การเรียนรู้", "อาหารไทย", "เทคโนโลยี"]
            
            results = []
            
            # Benchmark tokenization
            logger.info("Running tokenization benchmark...")
            tokenization_result = self.benchmark_tokenization(text_samples[:10])
            results.append(tokenization_result)
            
            # Benchmark API tokenization (if service is available)
            try:
                logger.info("Running API tokenization benchmark...")
                api_result = await self.benchmark_api_tokenization(text_samples[:5], concurrent_requests=5)
                results.append(api_result)
            except Exception as e:
                logger.warning(f"API benchmark skipped: {e}")
            
            # Benchmark indexing
            logger.info("Running indexing benchmark...")
            indexing_result = self.benchmark_indexing(documents[:20])
            results.append(indexing_result)
            
            # Benchmark search (requires existing index)
            try:
                logger.info("Running search benchmark...")
                search_result = self.benchmark_search(queries)
                results.append(search_result)
            except Exception as e:
                logger.warning(f"Search benchmark skipped: {e}")
            
            # Print and save results
            self.print_benchmark_report(results)
            self.save_benchmark_report(results)
            
            logger.info("Benchmark completed successfully!")
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            raise


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Thai tokenizer performance benchmarks")
    parser.add_argument("--meilisearch-host", default="http://localhost:7700",
                       help="MeiliSearch host URL")
    parser.add_argument("--api-key", default="masterKey",
                       help="MeiliSearch API key")
    parser.add_argument("--tokenizer-host", default="http://localhost:8000",
                       help="Thai tokenizer service host URL")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(
        meilisearch_host=args.meilisearch_host,
        api_key=args.api_key,
        tokenizer_host=args.tokenizer_host
    )
    await benchmark.run_full_benchmark()


if __name__ == "__main__":
    asyncio.run(main())