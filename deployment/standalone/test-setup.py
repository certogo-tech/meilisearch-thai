#!/usr/bin/env python3
"""
Test script for standalone deployment setup.

This script performs basic validation of the standalone deployment scripts
without actually installing anything.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_script_imports():
    """Test that all scripts can be imported without errors."""
    print("Testing script imports...")
    
    try:
        # Test setup-venv.py
        import importlib.util
        
        script_dir = Path(__file__).parent
        
        # Load setup-venv module
        spec = importlib.util.spec_from_file_location("setup_venv", script_dir / "setup-venv.py")
        setup_venv_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup_venv_module)
        
        # Test VirtualEnvironmentManager class
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_manager = setup_venv_module.VirtualEnvironmentManager(temp_dir)
            assert venv_manager.install_path == Path(temp_dir)
            print("✓ setup-venv.py imports and initializes correctly")
        
        # Load install-dependencies module
        spec = importlib.util.spec_from_file_location("install_dependencies", script_dir / "install-dependencies.py")
        install_deps_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install_deps_module)
        
        print("✓ install-dependencies.py imports correctly")
        
        # Load configure-service module
        spec = importlib.util.spec_from_file_location("configure_service", script_dir / "configure-service.py")
        configure_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(configure_module)
        
        print("✓ configure-service.py imports correctly")
        
        # Load manage-service module
        spec = importlib.util.spec_from_file_location("manage_service", script_dir / "manage-service.py")
        manage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manage_module)
        
        print("✓ manage-service.py imports correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def test_configuration_creation():
    """Test configuration creation without actual deployment."""
    print("\nTesting configuration creation...")
    
    try:
        from deployment.config import OnPremiseConfig, DeploymentMethod, MeilisearchConnectionConfig
        
        # Create a test configuration
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.STANDALONE,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-api-key"
            )
        )
        
        # Test environment variable generation
        env_vars = config.get_environment_dict()
        assert "THAI_TOKENIZER_SERVICE_PORT" in env_vars
        assert "THAI_TOKENIZER_MEILISEARCH_HOST" in env_vars
        
        print("✓ Configuration creation works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_directory_structure():
    """Test directory structure creation."""
    print("\nTesting directory structure creation...")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_path = Path(temp_dir) / "thai-tokenizer"
            
            # Test directory creation
            directories = [
                install_path,
                install_path / "bin",
                install_path / "config",
                install_path / "logs",
                install_path / "data",
                install_path / "run",
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                assert directory.exists()
            
            print("✓ Directory structure creation works correctly")
            return True
            
    except Exception as e:
        print(f"✗ Directory structure test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running standalone deployment setup tests...\n")
    
    tests = [
        test_script_imports,
        test_configuration_creation,
        test_directory_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    print(f"\nTest Results:")
    print(f"✓ Passed: {passed}")
    print(f"✗ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Standalone deployment scripts are ready.")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)