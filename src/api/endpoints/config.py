"""Configuration management endpoints for the Thai tokenizer API."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.api.models.requests import MeiliSearchConfigRequest, TokenizerConfigRequest
from src.api.models.responses import ConfigurationResponse, ErrorResponse
from src.tokenizer.config_manager import ConfigManager
from src.meilisearch_integration.client import MeiliSearchClient
from src.meilisearch_integration.settings_manager import TokenizationSettingsManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (will be injected via dependency injection)
_config_manager: ConfigManager = None
_meilisearch_client: MeiliSearchClient = None
_settings_manager: TokenizationSettingsManager = None


def get_config_manager() -> ConfigManager:
    """Dependency to get configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_meilisearch_client() -> MeiliSearchClient:
    """Dependency to get MeiliSearch client instance."""
    global _meilisearch_client
    if _meilisearch_client is None:
        # Create a default config for the client
        from src.meilisearch_integration.client import MeiliSearchConfig
        default_config = MeiliSearchConfig(
            host="http://localhost:7700",
            api_key="masterKey",
            timeout=30,
            max_retries=3
        )
        _meilisearch_client = MeiliSearchClient(config=default_config)
    return _meilisearch_client


def get_settings_manager() -> TokenizationSettingsManager:
    """Dependency to get settings manager instance."""
    global _settings_manager, _meilisearch_client
    if _settings_manager is None:
        if _meilisearch_client is None:
            _meilisearch_client = get_meilisearch_client()
        _settings_manager = TokenizationSettingsManager(meilisearch_client=_meilisearch_client)
    return _settings_manager


@router.get("/config")
async def get_current_configuration(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Retrieve current configuration settings.
    
    Returns the current configuration for both the tokenizer and MeiliSearch
    integration, including connection settings and processing parameters.
    """
    try:
        logger.info("Retrieving current configuration")
        
        # Get current configuration as dictionary
        config = config_manager.to_dict()
        
        # Mask sensitive information
        masked_config = config.copy()
        if "meilisearch_api_key" in masked_config:
            api_key = masked_config["meilisearch_api_key"]
            if api_key and len(api_key) > 8:
                masked_config["meilisearch_api_key"] = f"{api_key[:8]}{'*' * (len(api_key) - 8)}"
        
        # Get configuration stats
        stats = config_manager.get_stats()
        
        response = {
            "configuration": masked_config,
            "status": "active" if stats["validation_status"] else "invalid",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Configuration retrieved successfully")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="config_retrieval_error",
                message=f"Failed to retrieve configuration: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.put("/config/meilisearch", response_model=ConfigurationResponse)
async def update_meilisearch_configuration(
    request: MeiliSearchConfigRequest,
    config_manager: ConfigManager = Depends(get_config_manager),
    meilisearch_client: MeiliSearchClient = Depends(get_meilisearch_client),
    settings_manager: TokenizationSettingsManager = Depends(get_settings_manager)
):
    """
    Update MeiliSearch connection and configuration settings.
    
    This endpoint updates the MeiliSearch connection parameters and applies
    Thai tokenization settings to the specified index.
    """
    try:
        logger.info(f"Updating MeiliSearch configuration for host: {request.host}")
        
        # Validate the configuration by testing connection
        test_client = MeiliSearchClient(
            host=request.host,
            api_key=request.api_key
        )
        
        # Test connection
        if not await test_client.health_check():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot connect to MeiliSearch with provided settings"
            )
        
        # Create MeiliSearchConfig object and update configuration
        from src.tokenizer.config_manager import MeiliSearchConfig
        
        meilisearch_config = MeiliSearchConfig(
            host=request.host,
            api_key=request.api_key,
            index_name=request.index_name
        )
        
        config_manager.update_meilisearch_config(meilisearch_config)
        
        # Update the client instance
        meilisearch_client.update_connection(
            host=request.host,
            api_key=request.api_key
        )
        
        # Apply Thai tokenization settings to the index
        try:
            await settings_manager.configure_thai_tokenization(request.index_name)
            logger.info(f"Thai tokenization settings applied to index: {request.index_name}")
        except Exception as e:
            logger.warning(f"Failed to apply Thai tokenization settings: {e}")
            # Continue anyway as the connection update was successful
        
        response = ConfigurationResponse(
            status="updated",
            message=f"MeiliSearch configuration updated for index '{request.index_name}'",
            applied_at=datetime.now()
        )
        
        logger.info("MeiliSearch configuration updated successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update MeiliSearch configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="meilisearch_config_error",
                message=f"Failed to update MeiliSearch configuration: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.put("/config/tokenizer", response_model=ConfigurationResponse)
async def update_tokenizer_configuration(
    request: TokenizerConfigRequest,
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Update tokenizer configuration settings.
    
    This endpoint updates the Thai tokenizer configuration including
    the tokenization engine, custom dictionary, and processing parameters.
    """
    try:
        logger.info(f"Updating tokenizer configuration: engine={request.engine}")
        
        # Validate tokenizer engine
        valid_engines = ["pythainlp", "newmm", "attacut", "deepcut"]
        if request.engine not in valid_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tokenizer engine. Must be one of: {valid_engines}"
            )
        
        # Validate fallback engine if provided
        if request.fallback_engine and request.fallback_engine not in valid_engines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid fallback engine. Must be one of: {valid_engines}"
            )
        
        # Validate parameters
        if request.batch_size <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size must be greater than 0"
            )
        
        if request.max_retries < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max retries must be non-negative"
            )
        
        if request.timeout_ms <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Timeout must be greater than 0"
            )
        
        # Create TokenizerConfig object and update configuration
        from src.tokenizer.config_manager import TokenizerConfig
        
        tokenizer_config = TokenizerConfig(
            engine=request.engine,
            model_version=request.model_version,
            custom_dictionary=request.custom_dictionary or [],
            keep_whitespace=request.keep_whitespace,
            handle_compounds=request.handle_compounds,
            fallback_engine=request.fallback_engine
        )
        
        config_manager.update_tokenizer_config(tokenizer_config)
        
        # Update processing configuration separately
        config_manager.settings.processing_batch_size = request.batch_size
        config_manager.settings.processing_max_concurrent = request.max_retries  # Note: this maps to max_concurrent, not retries
        config_manager.settings.meilisearch_timeout_ms = request.timeout_ms
        
        response = ConfigurationResponse(
            status="updated",
            message=f"Tokenizer configuration updated with engine '{request.engine}'",
            applied_at=datetime.now()
        )
        
        logger.info("Tokenizer configuration updated successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tokenizer configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="tokenizer_config_error",
                message=f"Failed to update tokenizer configuration: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/config/validate")
async def validate_configuration(
    config_manager: ConfigManager = Depends(get_config_manager),
    meilisearch_client: MeiliSearchClient = Depends(get_meilisearch_client)
):
    """
    Validate current configuration settings.
    
    This endpoint tests the current configuration by checking MeiliSearch
    connectivity, tokenizer functionality, and overall system health.
    """
    try:
        logger.info("Validating current configuration")
        
        validation_results = {
            "overall_status": "valid",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Check MeiliSearch connection
        try:
            meilisearch_healthy = await meilisearch_client.health_check()
            validation_results["checks"]["meilisearch_connection"] = {
                "status": "valid" if meilisearch_healthy else "invalid",
                "message": "Connection successful" if meilisearch_healthy else "Connection failed"
            }
        except Exception as e:
            validation_results["checks"]["meilisearch_connection"] = {
                "status": "invalid",
                "message": f"Connection error: {str(e)}"
            }
            validation_results["overall_status"] = "invalid"
        
        # Check tokenizer configuration
        try:
            tokenizer_config = config_manager.get_tokenizer_config()
            
            # Validate tokenizer engine
            engine = tokenizer_config.engine.value
            valid_engines = ["pythainlp", "newmm", "attacut", "deepcut"]
            
            if engine in valid_engines:
                validation_results["checks"]["tokenizer_engine"] = {
                    "status": "valid",
                    "message": f"Engine '{engine}' is supported"
                }
            else:
                validation_results["checks"]["tokenizer_engine"] = {
                    "status": "invalid",
                    "message": f"Engine '{engine}' is not supported"
                }
                validation_results["overall_status"] = "invalid"
                
        except Exception as e:
            validation_results["checks"]["tokenizer_configuration"] = {
                "status": "invalid",
                "message": f"Configuration error: {str(e)}"
            }
            validation_results["overall_status"] = "invalid"
        
        # Check index configuration
        try:
            meilisearch_config = config_manager.get_meilisearch_config()
            index_name = meilisearch_config.index_name
            
            if index_name:
                # Try to get index info
                index_exists = await meilisearch_client.index_exists(index_name)
                validation_results["checks"]["index_configuration"] = {
                    "status": "valid" if index_exists else "warning",
                    "message": f"Index '{index_name}' {'exists' if index_exists else 'does not exist (will be created on first use)'}"
                }
            else:
                validation_results["checks"]["index_configuration"] = {
                    "status": "invalid",
                    "message": "No index name configured"
                }
                validation_results["overall_status"] = "invalid"
                
        except Exception as e:
            validation_results["checks"]["index_configuration"] = {
                "status": "invalid",
                "message": f"Index check error: {str(e)}"
            }
            validation_results["overall_status"] = "invalid"
        
        logger.info(f"Configuration validation completed: {validation_results['overall_status']}")
        return validation_results
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="validation_error",
                message=f"Failed to validate configuration: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/config/dictionary/add")
async def add_dictionary_words(
    words: List[str],
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Add words to the custom dictionary.
    
    This endpoint allows adding new words to the custom dictionary
    used for Thai tokenization enhancement.
    """
    try:
        logger.info(f"Adding {len(words)} words to custom dictionary")
        
        if not words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No words provided"
            )
        
        # Validate words
        valid_words = []
        for word in words:
            if not isinstance(word, str):
                continue
            word = word.strip()
            if word and len(word) > 0:
                valid_words.append(word)
        
        if not valid_words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid words provided"
            )
        
        # Add words to dictionary
        config_manager.add_custom_dictionary_words(valid_words)
        
        response = {
            "status": "added",
            "message": f"Added {len(valid_words)} words to custom dictionary",
            "added_words": valid_words,
            "total_dictionary_size": len(config_manager._custom_dictionary),
            "added_at": datetime.now().isoformat()
        }
        
        logger.info(f"Successfully added {len(valid_words)} words to custom dictionary")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add dictionary words: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="dictionary_add_error",
                message=f"Failed to add dictionary words: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/config/dictionary/remove")
async def remove_dictionary_words(
    words: List[str],
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Remove words from the custom dictionary.
    
    This endpoint allows removing words from the custom dictionary
    used for Thai tokenization enhancement.
    """
    try:
        logger.info(f"Removing {len(words)} words from custom dictionary")
        
        if not words:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No words provided"
            )
        
        # Remove words from dictionary
        config_manager.remove_custom_dictionary_words(words)
        
        response = {
            "status": "removed",
            "message": f"Processed removal of {len(words)} words from custom dictionary",
            "requested_words": words,
            "total_dictionary_size": len(config_manager._custom_dictionary),
            "removed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Successfully processed removal of {len(words)} words from custom dictionary")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove dictionary words: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="dictionary_remove_error",
                message=f"Failed to remove dictionary words: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/config/dictionary")
async def get_custom_dictionary(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Get the current custom dictionary.
    
    Returns the list of custom dictionary words currently configured
    for Thai tokenization enhancement.
    """
    try:
        logger.info("Retrieving custom dictionary")
        
        dictionary = config_manager._custom_dictionary
        
        response = {
            "dictionary": dictionary,
            "size": len(dictionary),
            "retrieved_at": datetime.now().isoformat()
        }
        
        logger.info(f"Retrieved custom dictionary with {len(dictionary)} words")
        return response
        
    except Exception as e:
        logger.error(f"Failed to retrieve custom dictionary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="dictionary_retrieval_error",
                message=f"Failed to retrieve custom dictionary: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/config/validation")
async def get_configuration_validation(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Get detailed configuration validation report.
    
    Returns a comprehensive validation report for all configuration
    components including errors, warnings, and component status.
    """
    try:
        logger.info("Generating configuration validation report")
        
        validation_report = config_manager.validate_configuration()
        validation_report["generated_at"] = datetime.now().isoformat()
        
        logger.info(f"Configuration validation report generated: {validation_report['valid']}")
        return validation_report
        
    except Exception as e:
        logger.error(f"Failed to generate validation report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="validation_report_error",
                message=f"Failed to generate validation report: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/config/reset")
async def reset_configuration(
    config_manager: ConfigManager = Depends(get_config_manager)
):
    """
    Reset configuration to default values.
    
    This endpoint resets both tokenizer and MeiliSearch configuration
    to their default values. Use with caution.
    """
    try:
        logger.info("Resetting configuration to defaults")
        
        # Create new default settings and update the config manager
        from src.tokenizer.config_manager import ThaiTokenizerSettings, MeiliSearchConfig, TokenizerConfig
        
        # Reset to default settings
        default_settings = ThaiTokenizerSettings()
        config_manager._settings = default_settings
        config_manager._custom_dictionary = []
        
        response = {
            "status": "reset",
            "message": "Configuration reset to default values",
            "reset_at": datetime.now().isoformat(),
            "warning": "All custom settings have been cleared"
        }
        
        logger.info("Configuration reset completed")
        return response
        
    except Exception as e:
        logger.error(f"Failed to reset configuration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="reset_error",
                message=f"Failed to reset configuration: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )