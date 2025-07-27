#!/usr/bin/env python3
"""
Demo runner script for Thai Tokenizer MeiliSearch integration.

This script provides a simple interface to run all demonstration scripts
in the correct order with proper error handling and logging.
"""

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import httpx


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoRunner:
    """Orchestrate and run all demonstration scripts."""
    
    def __init__(self, meilisearch_host: str = "http://localhost:7700",
                 api_key: str = "masterKey",
                 tokenizer_host: str = "http://localhost:8000"):
        """Initialize demo runner."""
        self.meilisearch_host = meilisearch_host
        self.api_key = api_key
        self.tokenizer_host = tokenizer_host
        self.scripts_dir = Path(__file__).parent
        
    async def check_services(self) -> bool:
        """Check if required services are running."""
        logger.info("Checking service availability...")
        
        services_ok = True
        
        # Check MeiliSearch
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.meilisearch_host}/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info("✓ MeiliSearch is running")
                else:
                    logger.error(f"✗ MeiliSearch returned status {response.status_code}")
                    services_ok = False
        except Exception as e:
            logger.error(f"✗ MeiliSearch not available: {e}")
            services_ok = False
        
        # Check Thai tokenizer service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.tokenizer_host}/health", timeout=5.0)
                if response.status_code == 200:
                    logger.info("✓ Thai tokenizer service is running")
                else:
                    logger.warning(f"⚠ Thai tokenizer service returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠ Thai tokenizer service not available: {e}")
            logger.info("  Demo will continue with limited functionality")
        
        return services_ok
    
    def run_script(self, script_name: str, args: List[str] = None) -> bool:
        """Run a Python script with error handling."""
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return False
        
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✓ {script_name} completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
            else:
                logger.error(f"✗ {script_name} failed with return code {result.returncode}")
                if result.stderr:
                    logger.error(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {script_name} timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"✗ Failed to run {script_name}: {e}")
            return False
    
    def print_demo_header(self) -> None:
        """Print demo introduction."""
        print("\n" + "=" * 80)
        print("THAI TOKENIZER FOR MEILISEARCH - DEMONSTRATION SUITE")
        print("=" * 80)
        print("\nThis demo will:")
        print("1. Set up sample Thai documents in MeiliSearch")
        print("2. Compare search results before/after tokenization")
        print("3. Run performance benchmarks")
        print("\nMake sure you have the following services running:")
        print("- MeiliSearch at http://localhost:7700")
        print("- Thai Tokenizer API at http://localhost:8000 (optional)")
        print("\nYou can start services with: docker-compose up -d")
        print("=" * 80)
    
    def print_demo_footer(self, success: bool) -> None:
        """Print demo conclusion."""
        print("\n" + "=" * 80)
        if success:
            print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
            print("\nNext steps:")
            print("- Explore the MeiliSearch interface at http://localhost:7700")
            print("- Try the Thai Tokenizer API at http://localhost:8000/docs")
            print("- Review generated reports: comparison_report.json, benchmark_report.json")
            print("- Check sample data in the sample_data/ directory")
        else:
            print("DEMONSTRATION COMPLETED WITH ERRORS")
            print("\nTroubleshooting:")
            print("- Check that services are running: docker-compose ps")
            print("- View service logs: docker-compose logs")
            print("- Ensure sample data files exist in sample_data/")
        print("=" * 80)
    
    async def run_full_demo(self, skip_setup: bool = False, 
                          skip_comparison: bool = False,
                          skip_benchmark: bool = False) -> None:
        """Run the complete demonstration suite."""
        self.print_demo_header()
        
        success = True
        
        try:
            # Check services
            if not await self.check_services():
                logger.error("Required services not available. Please start them first.")
                return
            
            # Step 1: Setup demo data
            if not skip_setup:
                logger.info("\n" + "=" * 50)
                logger.info("STEP 1: Setting up demo data")
                logger.info("=" * 50)
                
                setup_args = [
                    "--host", self.meilisearch_host,
                    "--api-key", self.api_key
                ]
                
                if not self.run_script("setup_demo.py", setup_args):
                    logger.error("Demo setup failed")
                    success = False
                else:
                    logger.info("Demo data setup completed")
                    time.sleep(2)  # Brief pause between steps
            
            # Step 2: Run comparison
            if not skip_comparison and success:
                logger.info("\n" + "=" * 50)
                logger.info("STEP 2: Comparing search results")
                logger.info("=" * 50)
                
                comparison_args = [
                    "--host", self.meilisearch_host,
                    "--api-key", self.api_key
                ]
                
                if not self.run_script("compare_results.py", comparison_args):
                    logger.warning("Comparison failed, but continuing...")
                else:
                    logger.info("Search comparison completed")
                    time.sleep(2)
            
            # Step 3: Run benchmarks
            if not skip_benchmark and success:
                logger.info("\n" + "=" * 50)
                logger.info("STEP 3: Running performance benchmarks")
                logger.info("=" * 50)
                
                benchmark_args = [
                    "--meilisearch-host", self.meilisearch_host,
                    "--api-key", self.api_key,
                    "--tokenizer-host", self.tokenizer_host
                ]
                
                if not self.run_script("benchmark.py", benchmark_args):
                    logger.warning("Benchmark failed, but demo completed")
                else:
                    logger.info("Performance benchmark completed")
            
        except KeyboardInterrupt:
            logger.info("\nDemo interrupted by user")
            success = False
        except Exception as e:
            logger.error(f"Demo failed with error: {e}")
            success = False
        
        self.print_demo_footer(success)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Thai Tokenizer demonstration suite")
    parser.add_argument("--meilisearch-host", default="http://localhost:7700",
                       help="MeiliSearch host URL")
    parser.add_argument("--api-key", default="masterKey",
                       help="MeiliSearch API key")
    parser.add_argument("--tokenizer-host", default="http://localhost:8000",
                       help="Thai tokenizer service host URL")
    parser.add_argument("--skip-setup", action="store_true",
                       help="Skip demo data setup")
    parser.add_argument("--skip-comparison", action="store_true",
                       help="Skip search comparison")
    parser.add_argument("--skip-benchmark", action="store_true",
                       help="Skip performance benchmark")
    
    args = parser.parse_args()
    
    runner = DemoRunner(
        meilisearch_host=args.meilisearch_host,
        api_key=args.api_key,
        tokenizer_host=args.tokenizer_host
    )
    
    await runner.run_full_demo(
        skip_setup=args.skip_setup,
        skip_comparison=args.skip_comparison,
        skip_benchmark=args.skip_benchmark
    )


if __name__ == "__main__":
    asyncio.run(main())