#!/usr/bin/env python3
"""
Reindex Existing MeiliSearch Data with Thai Tokenization

This script extracts documents from existing MeiliSearch indexes,
processes them through the Thai tokenizer, and re-indexes them
with proper tokenized_content fields for compound word search.

Usage:
    python scripts/maintenance/reindex-existing-data.py --index research
    python scripts/maintenance/reindex-existing-data.py --all-indexes
    python scripts/maintenance/reindex-existing-data.py --dry-run
"""

import asyncio
import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.meilisearch_integration.client import MeiliSearchClient, MeiliSearchConfig
from src.meilisearch_integration.document_processor import DocumentProcessor
from src.tokenizer.config_manager import ConfigManager


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'reindex_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ReindexStats:
    """Statistics for reindexing operation."""
    index_name: str
    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    skipped_documents: int = 0
    processing_time_ms: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class MeiliSearchReindexer:
    """
    Handles reindexing of existing MeiliSearch data with Thai tokenization.
    """
    
    def __init__(self, config_manager: ConfigManager, dry_run: bool = False):
        """Initialize reindexer with configuration."""
        self.config_manager = config_manager
        self.dry_run = dry_run
        
        # Initialize MeiliSearch client
        meilisearch_config = config_manager.get_meilisearch_config()
        client_config = MeiliSearchConfig(
            host=meilisearch_config.host,
            api_key=meilisearch_config.api_key,
            timeout=meilisearch_config.timeout_ms // 1000,
            max_retries=meilisearch_config.max_retries
        )
        self.meilisearch_client = MeiliSearchClient(client_config)
        
        # Initialize document processor
        self.document_processor = DocumentProcessor(
            meilisearch_client=self.meilisearch_client,
            batch_size=50,  # Smaller batches for reindexing
            max_concurrent=5  # Conservative concurrency
        )
        
        logger.info(f"Initialized reindexer (dry_run={dry_run})")
        logger.info(f"MeiliSearch host: {meilisearch_config.host}")
    
    async def get_all_indexes(self) -> List[str]:
        """Get list of all available indexes."""
        try:
            # Use the client's internal method to get indexes
            indexes_response = await self.meilisearch_client._retry_operation(
                self.meilisearch_client.client.get_indexes
            )
            
            index_names = [idx["uid"] for idx in indexes_response["results"]]
            logger.info(f"Found {len(index_names)} indexes: {index_names}")
            return index_names
            
        except Exception as e:
            logger.error(f"Failed to get indexes: {e}")
            raise
    
    async def get_all_documents_from_index(self, index_name: str) -> List[Dict[str, Any]]:
        """
        Extract all documents from a MeiliSearch index.
        
        Args:
            index_name: Name of the index to extract from
            
        Returns:
            List of all documents in the index
        """
        try:
            logger.info(f"Extracting documents from index: {index_name}")
            
            # Get index reference
            index = await self.meilisearch_client.get_index(index_name)
            
            # Get all documents in batches
            all_documents = []
            offset = 0
            limit = 1000  # MeiliSearch limit per request
            
            while True:
                # Get batch of documents
                batch = await self.meilisearch_client._retry_operation(
                    index.get_documents,
                    {"offset": offset, "limit": limit}
                )
                
                documents = batch.get("results", [])
                if not documents:
                    break
                
                all_documents.extend(documents)
                logger.info(f"Extracted {len(documents)} documents (total: {len(all_documents)})")
                
                # Check if we got fewer documents than requested (end of data)
                if len(documents) < limit:
                    break
                
                offset += limit
            
            logger.info(f"Total documents extracted from {index_name}: {len(all_documents)}")
            return all_documents
            
        except Exception as e:
            logger.error(f"Failed to extract documents from {index_name}: {e}")
            raise
    
    async def check_documents_need_reindexing(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check which documents need reindexing based on missing tokenized_content.
        
        Args:
            documents: List of documents to check
            
        Returns:
            Analysis of documents that need reindexing
        """
        needs_reindexing = []
        has_tokenized_content = []
        has_thai_content = []
        
        for doc in documents:
            doc_id = doc.get("id", "unknown")
            
            # Check if document has tokenized_content field
            if not doc.get("tokenized_content"):
                needs_reindexing.append(doc_id)
                
                # Check if document has Thai content
                title = doc.get("title", "")
                content = doc.get("content", "")
                full_text = f"{title} {content}"
                
                # Simple Thai detection
                thai_chars = sum(1 for c in full_text if '\\u0e00' <= c <= '\\u0e7f')
                if thai_chars > 0:
                    has_thai_content.append(doc_id)
            else:
                has_tokenized_content.append(doc_id)
        
        analysis = {
            "total_documents": len(documents),
            "needs_reindexing": len(needs_reindexing),
            "already_tokenized": len(has_tokenized_content),
            "has_thai_content": len(has_thai_content),
            "documents_to_process": needs_reindexing[:10],  # Sample
            "recommendation": self._get_reindexing_recommendation(
                len(documents), len(needs_reindexing), len(has_thai_content)
            )
        }
        
        return analysis
    
    def _get_reindexing_recommendation(self, total: int, needs_reindexing: int, has_thai: int) -> str:
        """Get recommendation based on analysis."""
        if needs_reindexing == 0:
            return "✅ No reindexing needed - all documents have tokenized_content"
        elif needs_reindexing == total:
            return "🔄 Full reindexing recommended - no documents have tokenized_content"
        elif has_thai > 0:
            return f"⚠️ Partial reindexing needed - {needs_reindexing} documents missing tokenized_content, {has_thai} have Thai content"
        else:
            return "ℹ️ Documents missing tokenized_content but no Thai content detected"
    
    async def reindex_documents(
        self, 
        index_name: str, 
        documents: List[Dict[str, Any]],
        backup_index: bool = True
    ) -> ReindexStats:
        """
        Reindex documents with Thai tokenization.
        
        Args:
            index_name: Name of the index to reindex
            documents: Documents to reindex
            backup_index: Whether to create backup before reindexing
            
        Returns:
            Reindexing statistics
        """
        start_time = time.time()
        stats = ReindexStats(index_name=index_name, total_documents=len(documents))
        
        try:
            logger.info(f"Starting reindexing of {len(documents)} documents in {index_name}")
            
            if self.dry_run:
                logger.info("DRY RUN: Would reindex documents but not making actual changes")
                stats.processed_documents = len(documents)
                stats.processing_time_ms = (time.time() - start_time) * 1000
                return stats
            
            # Create backup if requested
            if backup_index:
                backup_name = f"{index_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await self._create_backup_index(index_name, backup_name, documents)
                logger.info(f"Created backup index: {backup_name}")
            
            # Filter documents that need processing
            documents_to_process = [
                doc for doc in documents 
                if not doc.get("tokenized_content")
            ]
            
            if not documents_to_process:
                logger.info("No documents need reindexing")
                stats.skipped_documents = len(documents)
                return stats
            
            logger.info(f"Processing {len(documents_to_process)} documents that need tokenization")
            
            # Process documents through Thai tokenizer
            batch_result = await self.document_processor.process_batch(
                documents_to_process,
                preserve_original=True
            )
            
            # Update statistics
            stats.processed_documents = batch_result.processed_count
            stats.failed_documents = batch_result.failed_count
            stats.skipped_documents = batch_result.skipped_count + (len(documents) - len(documents_to_process))
            stats.errors = [error.get("error", str(error)) for error in batch_result.errors]
            
            # Index processed documents back to MeiliSearch
            if batch_result.processed_documents:
                index_result = await self.document_processor.index_processed_documents(
                    batch_result.processed_documents,
                    index_name,
                    update_existing=True
                )
                
                logger.info(f"Indexed {index_result.get('indexed_count', 0)} processed documents")
            
            stats.processing_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Reindexing completed for {index_name}: "
                f"{stats.processed_documents} processed, "
                f"{stats.failed_documents} failed, "
                f"{stats.skipped_documents} skipped "
                f"({stats.processing_time_ms:.2f}ms)"
            )
            
            return stats
            
        except Exception as e:
            error_msg = f"Reindexing failed for {index_name}: {str(e)}"
            logger.error(error_msg)
            stats.errors.append(error_msg)
            stats.failed_documents = len(documents)
            stats.processing_time_ms = (time.time() - start_time) * 1000
            return stats
    
    async def _create_backup_index(
        self, 
        source_index: str, 
        backup_index: str, 
        documents: List[Dict[str, Any]]
    ):
        """Create a backup index with original documents."""
        try:
            # Create backup index
            await self.meilisearch_client.create_index(backup_index)
            
            # Copy settings from source index
            source_settings = await self.meilisearch_client.get_index_settings(source_index)
            await self.meilisearch_client.update_index_settings(backup_index, source_settings)
            
            # Add documents to backup index
            await self.meilisearch_client.add_documents(backup_index, documents)
            
            logger.info(f"Backup created: {backup_index} with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to create backup {backup_index}: {e}")
            raise
    
    async def reindex_single_index(
        self, 
        index_name: str, 
        force: bool = False,
        backup: bool = True
    ) -> ReindexStats:
        """
        Reindex a single MeiliSearch index.
        
        Args:
            index_name: Name of the index to reindex
            force: Force reindexing even if not needed
            backup: Create backup before reindexing
            
        Returns:
            Reindexing statistics
        """
        try:
            logger.info(f"Starting reindexing process for index: {index_name}")
            
            # Check if index exists
            if not await self.meilisearch_client.index_exists(index_name):
                raise ValueError(f"Index '{index_name}' does not exist")
            
            # Extract all documents
            documents = await self.get_all_documents_from_index(index_name)
            
            if not documents:
                logger.warning(f"No documents found in index: {index_name}")
                return ReindexStats(index_name=index_name)
            
            # Analyze documents
            analysis = await self.check_documents_need_reindexing(documents)
            logger.info(f"Analysis for {index_name}: {analysis['recommendation']}")
            logger.info(f"Documents needing reindexing: {analysis['needs_reindexing']}/{analysis['total_documents']}")
            
            # Check if reindexing is needed
            if analysis['needs_reindexing'] == 0 and not force:
                logger.info(f"Index {index_name} already has tokenized content, skipping")
                return ReindexStats(
                    index_name=index_name,
                    total_documents=analysis['total_documents'],
                    skipped_documents=analysis['total_documents']
                )
            
            # Perform reindexing
            stats = await self.reindex_documents(index_name, documents, backup)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to reindex {index_name}: {e}")
            return ReindexStats(
                index_name=index_name,
                errors=[str(e)]
            )
    
    async def reindex_all_indexes(
        self, 
        exclude_indexes: List[str] = None,
        force: bool = False,
        backup: bool = True
    ) -> Dict[str, ReindexStats]:
        """
        Reindex all MeiliSearch indexes.
        
        Args:
            exclude_indexes: List of indexes to exclude
            force: Force reindexing even if not needed
            backup: Create backup before reindexing
            
        Returns:
            Dictionary of reindexing statistics per index
        """
        exclude_indexes = exclude_indexes or []
        results = {}
        
        try:
            # Get all indexes
            all_indexes = await self.get_all_indexes()
            
            # Filter indexes
            indexes_to_process = [
                idx for idx in all_indexes 
                if idx not in exclude_indexes
            ]
            
            logger.info(f"Reindexing {len(indexes_to_process)} indexes: {indexes_to_process}")
            
            # Process each index
            for index_name in indexes_to_process:
                logger.info(f"\\n{'='*60}")
                logger.info(f"Processing index: {index_name}")
                logger.info(f"{'='*60}")
                
                stats = await self.reindex_single_index(index_name, force, backup)
                results[index_name] = stats
                
                # Brief pause between indexes
                await asyncio.sleep(1)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to reindex all indexes: {e}")
            raise
    
    async def generate_reindex_report(self, results: Dict[str, ReindexStats]) -> str:
        """Generate a comprehensive reindexing report."""
        report_lines = [
            "\\n" + "="*80,
            "MEILISEARCH REINDEXING REPORT",
            "="*80,
            f"Generated: {datetime.now().isoformat()}",
            f"Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}",
            ""
        ]
        
        # Summary statistics
        total_docs = sum(stats.total_documents for stats in results.values())
        total_processed = sum(stats.processed_documents for stats in results.values())
        total_failed = sum(stats.failed_documents for stats in results.values())
        total_skipped = sum(stats.skipped_documents for stats in results.values())
        total_time = sum(stats.processing_time_ms for stats in results.values())
        
        report_lines.extend([
            "SUMMARY:",
            f"  Indexes processed: {len(results)}",
            f"  Total documents: {total_docs:,}",
            f"  Processed: {total_processed:,}",
            f"  Failed: {total_failed:,}",
            f"  Skipped: {total_skipped:,}",
            f"  Total processing time: {total_time/1000:.2f}s",
            ""
        ])
        
        # Per-index details
        report_lines.append("DETAILS BY INDEX:")
        for index_name, stats in results.items():
            status = "✅ SUCCESS" if stats.failed_documents == 0 else "❌ ERRORS"
            report_lines.extend([
                f"\\n  {index_name}: {status}",
                f"    Total documents: {stats.total_documents:,}",
                f"    Processed: {stats.processed_documents:,}",
                f"    Failed: {stats.failed_documents:,}",
                f"    Skipped: {stats.skipped_documents:,}",
                f"    Processing time: {stats.processing_time_ms/1000:.2f}s"
            ])
            
            if stats.errors:
                report_lines.append("    Errors:")
                for error in stats.errors[:3]:  # Show first 3 errors
                    report_lines.append(f"      - {error}")
                if len(stats.errors) > 3:
                    report_lines.append(f"      ... and {len(stats.errors) - 3} more errors")
        
        # Recommendations
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
        ])
        
        if total_failed > 0:
            report_lines.append("  ⚠️ Some documents failed to process - check logs for details")
        
        if total_processed > 0:
            report_lines.append("  ✅ Reindexing completed - Thai compound word search should now work")
            report_lines.append("  🔍 Test search with: วากาเมะ, รูเมน, ซูชิ, เทมปุระ")
        
        if total_skipped == total_docs:
            report_lines.append("  ℹ️ All documents already have tokenized content")
        
        report_lines.extend([
            "",
            "NEXT STEPS:",
            "  1. Test search quality: ./scripts/testing/test-all-indexes.sh",
            "  2. Verify compound words: ./scripts/testing/test-wakame-tokenization.sh",
            "  3. Check frontend integration with updated indexes",
            "",
            "="*80
        ])
        
        return "\\n".join(report_lines)
    
    async def close(self):
        """Clean up resources."""
        await self.meilisearch_client.close()


async def main():
    """Main entry point for the reindexing script."""
    parser = argparse.ArgumentParser(
        description="Reindex existing MeiliSearch data with Thai tokenization"
    )
    parser.add_argument(
        "--index", 
        type=str, 
        help="Specific index to reindex (e.g., 'research')"
    )
    parser.add_argument(
        "--all-indexes", 
        action="store_true", 
        help="Reindex all available indexes"
    )
    parser.add_argument(
        "--exclude", 
        type=str, 
        nargs="*", 
        default=[], 
        help="Indexes to exclude from reindexing"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force reindexing even if documents already have tokenized_content"
    )
    parser.add_argument(
        "--no-backup", 
        action="store_true", 
        help="Skip creating backup indexes"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.index and not args.all_indexes:
        parser.error("Must specify either --index or --all-indexes")
    
    if args.index and args.all_indexes:
        parser.error("Cannot specify both --index and --all-indexes")
    
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        if args.config:
            config_manager.load_config(args.config)
        
        # Initialize reindexer
        reindexer = MeiliSearchReindexer(config_manager, dry_run=args.dry_run)
        
        # Perform reindexing
        if args.index:
            logger.info(f"Reindexing single index: {args.index}")
            stats = await reindexer.reindex_single_index(
                args.index, 
                force=args.force, 
                backup=not args.no_backup
            )
            results = {args.index: stats}
        else:
            logger.info("Reindexing all indexes")
            results = await reindexer.reindex_all_indexes(
                exclude_indexes=args.exclude,
                force=args.force,
                backup=not args.no_backup
            )
        
        # Generate and display report
        report = await reindexer.generate_reindex_report(results)
        print(report)
        
        # Save report to file
        report_file = f"reindex_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to: {report_file}")
        
        # Clean up
        await reindexer.close()
        
        # Exit with appropriate code
        total_failed = sum(stats.failed_documents for stats in results.values())
        sys.exit(1 if total_failed > 0 else 0)
        
    except KeyboardInterrupt:
        logger.info("Reindexing interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Reindexing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())