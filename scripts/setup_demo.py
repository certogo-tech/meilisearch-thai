#!/usr/bin/env python3
"""
Demo setup script for Thai Tokenizer MeiliSearch integration.

This script populates MeiliSearch with sample Thai documents and configures
the tokenization settings for optimal Thai compound word search.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import httpx
from meilisearch import Client as MeiliSearchClient
from meilisearch.errors import MeilisearchError

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tokenizer.thai_segmenter import ThaiSegmenter
from tokenizer.config_manager import ConfigManager
from meilisearch_integration.client import MeiliSearchClient as CustomClient, MeiliSearchConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoSetup:
    """Demo setup and data population for Thai tokenizer."""
    
    def __init__(self, meilisearch_host: str = "http://localhost:7700", 
                 api_key: str = "masterKey"):
        """Initialize demo setup."""
        self.meilisearch_host = meilisearch_host
        self.api_key = api_key
        self.client = MeiliSearchClient(url=meilisearch_host, api_key=api_key)
        self.tokenizer = ThaiSegmenter()
        self.sample_data_dir = Path(__file__).parent.parent / "sample_data"
        
    async def check_services(self) -> bool:
        """Check if required services are running."""
        logger.info("Checking service availability...")
        
        # Check MeiliSearch
        try:
            health = self.client.health()
            logger.info(f"MeiliSearch status: {health}")
        except Exception as e:
            logger.error(f"MeiliSearch not available: {e}")
            return False
            
        # Check Thai tokenizer service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info("Thai tokenizer service is running")
                else:
                    logger.warning(f"Thai tokenizer service status: {response.status_code}")
        except Exception as e:
            logger.warning(f"Thai tokenizer service not available: {e}")
            logger.info("Continuing with direct tokenization...")
            
        return True
    
    def load_sample_documents(self) -> List[Dict[str, Any]]:
        """Load all sample documents from JSON files."""
        all_documents = []
        
        # Load different document types
        document_files = [
            "thai_documents.json",
            "formal_documents.json", 
            "informal_documents.json"
        ]
        
        for filename in document_files:
            file_path = self.sample_data_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        documents = json.load(f)
                        all_documents.extend(documents)
                        logger.info(f"Loaded {len(documents)} documents from {filename}")
                except Exception as e:
                    logger.error(f"Error loading {filename}: {e}")
            else:
                logger.warning(f"Sample file not found: {filename}")
        
        logger.info(f"Total documents loaded: {len(all_documents)}")
        return all_documents
    
    def preprocess_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Preprocess documents with Thai tokenization."""
        processed_docs = []
        
        for doc in documents:
            try:
                # Tokenize Thai content
                title_tokens = self.tokenizer.tokenize(doc.get('title', ''))
                content_tokens = self.tokenizer.tokenize(doc.get('content', ''))
                
                # Create processed document
                processed_doc = {
                    'id': doc['id'],
                    'title': doc.get('title', ''),
                    'content': doc.get('content', ''),
                    'category': doc.get('category', 'general'),
                    'tags': doc.get('tags', []),
                    
                    # Add tokenized versions for better search
                    'title_tokenized': ' '.join(title_tokens),
                    'content_tokenized': ' '.join(content_tokens),
                    
                    # Add searchable combined field
                    'searchable_text': f"{doc.get('title', '')} {doc.get('content', '')}",
                    'searchable_text_tokenized': ' '.join(title_tokens + content_tokens),
                    
                    # Preserve metadata
                    'metadata': doc.get('metadata', {}),
                    'document_type': doc.get('document_type', 'general'),
                    'style': doc.get('style', 'neutral'),
                    
                    # Add processing timestamp
                    'processed_at': int(time.time())
                }
                
                processed_docs.append(processed_doc)
                
            except Exception as e:
                logger.error(f"Error processing document {doc.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        return processed_docs
    
    def configure_meilisearch_index(self, index_name: str = "thai_documents") -> None:
        """Configure MeiliSearch index for Thai text search."""
        try:
            # Create or get index
            index = self.client.index(index_name)
            
            # Configure searchable attributes
            searchable_attributes = [
                'title',
                'content', 
                'title_tokenized',
                'content_tokenized',
                'searchable_text',
                'searchable_text_tokenized',
                'tags',
                'category'
            ]
            index.update_searchable_attributes(searchable_attributes)
            
            # Configure filterable attributes
            filterable_attributes = [
                'category',
                'document_type',
                'style',
                'tags',
                'metadata.difficulty',
                'metadata.mixed_content'
            ]
            index.update_filterable_attributes(filterable_attributes)
            
            # Configure sortable attributes
            sortable_attributes = [
                'processed_at',
                'category'
            ]
            index.update_sortable_attributes(sortable_attributes)
            
            # Configure ranking rules for Thai text
            ranking_rules = [
                'words',
                'typo',
                'proximity',
                'attribute',
                'sort',
                'exactness'
            ]
            index.update_ranking_rules(ranking_rules)
            
            # Configure stop words (minimal for Thai)
            stop_words = []  # Thai doesn't typically use stop words
            index.update_stop_words(stop_words)
            
            # Configure synonyms for common Thai terms
            synonyms = {
                'AI': ['ปัญญาประดิษฐ์', 'เอไอ'],
                'ปัญญาประดิษฐ์': ['AI', 'เอไอ'],
                'การเรียนรู้ของเครื่อง': ['Machine Learning', 'ML'],
                'Machine Learning': ['การเรียนรู้ของเครื่อง', 'ML'],
                'กรุงเทพฯ': ['กรุงเทพมหานคร', 'Bangkok'],
                'Bangkok': ['กรุงเทพฯ', 'กรุงเทพมหานคร']
            }
            index.update_synonyms(synonyms)
            
            logger.info(f"Configured MeiliSearch index: {index_name}")
            
        except MeilisearchError as e:
            logger.error(f"Error configuring MeiliSearch index: {e}")
            raise
    
    def populate_index(self, documents: List[Dict[str, Any]], 
                      index_name: str = "thai_documents") -> None:
        """Populate MeiliSearch index with processed documents."""
        try:
            index = self.client.index(index_name)
            
            # Add documents in batches
            batch_size = 10
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                task = index.add_documents(batch)
                logger.info(f"Added batch {i//batch_size + 1}: documents {i+1}-{min(i+batch_size, len(documents))}")
                
                # Wait for indexing to complete
                self.client.wait_for_task(task.task_uid)
            
            # Get final index stats
            stats = index.get_stats()
            logger.info(f"Index populated successfully: {stats}")
            
        except MeilisearchError as e:
            logger.error(f"Error populating index: {e}")
            raise
    
    def run_sample_searches(self, index_name: str = "thai_documents") -> None:
        """Run sample searches to demonstrate functionality."""
        logger.info("Running sample searches...")
        
        # Load test queries
        queries_file = self.sample_data_dir / "test_queries.json"
        if not queries_file.exists():
            logger.warning("Test queries file not found, skipping sample searches")
            return
            
        try:
            with open(queries_file, 'r', encoding='utf-8') as f:
                test_queries = json.load(f)
        except Exception as e:
            logger.error(f"Error loading test queries: {e}")
            return
        
        index = self.client.index(index_name)
        
        # Run a subset of test queries
        sample_queries = test_queries[:5]  # First 5 queries
        
        for query_data in sample_queries:
            query = query_data['query']
            description = query_data['description']
            
            try:
                # Search with different configurations
                results = index.search(query, {
                    'limit': 3,
                    'attributesToHighlight': ['title', 'content'],
                    'highlightPreTag': '<mark>',
                    'highlightPostTag': '</mark>'
                })
                
                logger.info(f"Query: '{query}' ({description})")
                logger.info(f"Found {results['estimatedTotalHits']} results in {results['processingTimeMs']}ms")
                
                for i, hit in enumerate(results['hits'][:2], 1):
                    logger.info(f"  {i}. {hit['title']} (category: {hit['category']})")
                
                logger.info("")
                
            except Exception as e:
                logger.error(f"Error searching for '{query}': {e}")
    
    async def run_demo(self) -> None:
        """Run the complete demo setup."""
        logger.info("Starting Thai Tokenizer Demo Setup")
        logger.info("=" * 50)
        
        try:
            # Check services
            if not await self.check_services():
                logger.error("Required services not available")
                return
            
            # Load sample documents
            logger.info("Loading sample documents...")
            documents = self.load_sample_documents()
            if not documents:
                logger.error("No documents loaded")
                return
            
            # Preprocess documents
            logger.info("Preprocessing documents with Thai tokenization...")
            processed_docs = self.preprocess_documents(documents)
            
            # Configure MeiliSearch
            logger.info("Configuring MeiliSearch index...")
            self.configure_meilisearch_index()
            
            # Populate index
            logger.info("Populating MeiliSearch index...")
            self.populate_index(processed_docs)
            
            # Run sample searches
            logger.info("Running sample searches...")
            self.run_sample_searches()
            
            logger.info("=" * 50)
            logger.info("Demo setup completed successfully!")
            logger.info("You can now:")
            logger.info("- Access MeiliSearch at http://localhost:7700")
            logger.info("- Use Thai tokenizer API at http://localhost:8000")
            logger.info("- Run search queries against the populated index")
            
        except Exception as e:
            logger.error(f"Demo setup failed: {e}")
            raise


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Thai Tokenizer Demo")
    parser.add_argument("--host", default="http://localhost:7700", 
                       help="MeiliSearch host URL")
    parser.add_argument("--api-key", default="masterKey",
                       help="MeiliSearch API key")
    parser.add_argument("--index", default="thai_documents",
                       help="Index name to create")
    
    args = parser.parse_args()
    
    demo = DemoSetup(meilisearch_host=args.host, api_key=args.api_key)
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())