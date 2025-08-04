"""
Configuration management API endpoints for Thai Search Proxy.

Provides endpoints to view and manage search proxy configuration
dynamically without service restart.
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from src.utils.logging import get_structured_logger
from src.api.middleware.auth import api_key_auth
from src.search_proxy.config.settings import (
    SearchProxySettings,
    TokenizationConfig,
    SearchConfig,
    RankingConfig,
    PerformanceConfig
)
from src.search_proxy.services.search_proxy_service import SearchProxyService
from src.api.endpoints.search_proxy import get_search_proxy_service

logger = get_structured_logger(__name__)

# Create router
router = APIRouter()


# Request/Response models
class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates."""
    config_type: str = Field(..., description="Type of configuration to update")
    config_data: Dict[str, Any] = Field(..., description="Configuration data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "config_type": "ranking",
                "config_data": {
                    "boost_exact_matches": 2.0,
                    "boost_thai_matches": 1.5
                }
            }
        }


class ConfigResponse(BaseModel):
    """Response model for configuration data."""
    config_type: str
    config_data: Dict[str, Any]
    last_updated: Optional[datetime] = None
    version: Optional[str] = None


class HotReloadStatusResponse(BaseModel):
    """Response model for hot reload status."""
    enabled: bool
    running: bool
    watched_paths: Dict[str, str]
    last_reload: Optional[datetime] = None
    reload_count: int = 0


@router.get(
    "/config",
    response_model=Dict[str, ConfigResponse],
    summary="Get all configuration",
    description="Retrieve all current configuration settings for the search proxy service."
)
async def get_all_config(
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> Dict[str, ConfigResponse]:
    """Get all current configuration settings."""
    
    logger.info("Configuration read requested")
    
    try:
        settings = service.settings
        
        configs = {
            "tokenization": ConfigResponse(
                config_type="tokenization",
                config_data=settings.tokenization.model_dump(),
                version=settings.service_version
            ),
            "search": ConfigResponse(
                config_type="search",
                config_data=settings.search.model_dump(),
                version=settings.service_version
            ),
            "ranking": ConfigResponse(
                config_type="ranking",
                config_data=settings.ranking.model_dump(),
                version=settings.service_version
            ),
            "performance": ConfigResponse(
                config_type="performance",
                config_data=settings.performance.model_dump(),
                version=settings.service_version
            )
        }
        
        return configs
        
    except Exception as e:
        logger.error(f"Failed to retrieve configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.get(
    "/config/{config_type}",
    response_model=ConfigResponse,
    summary="Get specific configuration",
    description="Retrieve a specific configuration section."
)
async def get_config(
    config_type: str,
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> ConfigResponse:
    """Get specific configuration section."""
    
    logger.info(f"Configuration read requested for: {config_type}")
    
    try:
        settings = service.settings
        
        config_mapping = {
            "tokenization": settings.tokenization,
            "search": settings.search,
            "ranking": settings.ranking,
            "performance": settings.performance,
            "service": {
                "service_name": settings.service_name,
                "service_version": settings.service_version,
                "environment": settings.environment
            }
        }
        
        if config_type not in config_mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration type '{config_type}' not found"
            )
        
        config_data = config_mapping[config_type]
        if hasattr(config_data, 'model_dump'):
            config_data = config_data.model_dump()
        
        return ConfigResponse(
            config_type=config_type,
            config_data=config_data,
            version=settings.service_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve {config_type} configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.put(
    "/config/{config_type}",
    response_model=ConfigResponse,
    summary="Update configuration",
    description="Update a specific configuration section. Requires hot reload to be enabled."
)
async def update_config(
    config_type: str,
    request: ConfigUpdateRequest,
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> ConfigResponse:
    """Update specific configuration section."""
    
    logger.info(f"Configuration update requested for: {config_type}")
    
    try:
        # Check if hot reload is enabled
        if not service._enable_hot_reload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hot reload is not enabled. Configuration updates require hot reload."
            )
        
        # Validate configuration type
        if config_type != request.config_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configuration type mismatch"
            )
        
        # Validate and update configuration
        settings = service.settings
        
        if config_type == "tokenization":
            new_config = TokenizationConfig(**request.config_data)
            settings.tokenization = new_config
        elif config_type == "search":
            new_config = SearchConfig(**request.config_data)
            settings.search = new_config
        elif config_type == "ranking":
            new_config = RankingConfig(**request.config_data)
            settings.ranking = new_config
        elif config_type == "performance":
            new_config = PerformanceConfig(**request.config_data)
            settings.performance = new_config
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration type '{config_type}' cannot be updated"
            )
        
        # Trigger configuration reload
        if service._hot_reload_manager:
            await service._on_config_reload(config_type)
        
        logger.info(f"Configuration {config_type} updated successfully")
        
        return ConfigResponse(
            config_type=config_type,
            config_data=request.config_data,
            last_updated=datetime.now(),
            version=settings.service_version
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update {config_type} configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.get(
    "/config/hot-reload/status",
    response_model=HotReloadStatusResponse,
    summary="Get hot reload status",
    description="Check the status of hot configuration reload."
)
async def get_hot_reload_status(
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> HotReloadStatusResponse:
    """Get hot reload configuration status."""
    
    try:
        if not service._hot_reload_manager:
            return HotReloadStatusResponse(
                enabled=service._enable_hot_reload,
                running=False,
                watched_paths={}
            )
        
        status = service._hot_reload_manager.get_config_status()
        
        return HotReloadStatusResponse(
            enabled=service._enable_hot_reload,
            running=status.get("running", False),
            watched_paths=status.get("watched_paths", {}),
            reload_count=len(status.get("cached_configs", []))
        )
        
    except Exception as e:
        logger.error(f"Failed to get hot reload status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hot reload status: {str(e)}"
        )


@router.post(
    "/config/hot-reload/trigger",
    summary="Trigger configuration reload",
    description="Manually trigger a configuration reload for a specific type."
)
async def trigger_reload(
    config_type: str,
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> Dict[str, str]:
    """Manually trigger configuration reload."""
    
    logger.info(f"Manual configuration reload triggered for: {config_type}")
    
    try:
        if not service._enable_hot_reload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hot reload is not enabled"
            )
        
        if not service._hot_reload_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hot reload manager not initialized"
            )
        
        # Trigger reload
        await service._on_config_reload(config_type)
        
        return {
            "status": "success",
            "message": f"Configuration reload triggered for {config_type}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger reload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger reload: {str(e)}"
        )


@router.get(
    "/config/defaults/{config_type}",
    response_model=ConfigResponse,
    summary="Get default configuration",
    description="Retrieve default configuration values for a specific type."
)
async def get_default_config(
    config_type: str,
    api_key: str = Depends(api_key_auth)
) -> ConfigResponse:
    """Get default configuration values."""
    
    try:
        defaults = {
            "tokenization": TokenizationConfig(),
            "search": SearchConfig(),
            "ranking": RankingConfig(),
            "performance": PerformanceConfig()
        }
        
        if config_type not in defaults:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration type '{config_type}' not found"
            )
        
        return ConfigResponse(
            config_type=config_type,
            config_data=defaults[config_type].model_dump(),
            version="default"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get default configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default configuration: {str(e)}"
        )


@router.post(
    "/config/validate",
    summary="Validate configuration",
    description="Validate configuration data without applying it."
)
async def validate_config(
    request: ConfigUpdateRequest,
    api_key: str = Depends(api_key_auth)
) -> Dict[str, Any]:
    """Validate configuration without applying."""
    
    try:
        config_type = request.config_type
        config_data = request.config_data
        
        # Try to create configuration object
        if config_type == "tokenization":
            TokenizationConfig(**config_data)
        elif config_type == "search":
            SearchConfig(**config_data)
        elif config_type == "ranking":
            RankingConfig(**config_data)
        elif config_type == "performance":
            PerformanceConfig(**config_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown configuration type: {config_type}"
            )
        
        return {
            "valid": True,
            "config_type": config_type,
            "message": "Configuration is valid"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "valid": False,
            "config_type": request.config_type,
            "message": f"Configuration validation failed: {str(e)}",
            "error": str(e)
        }