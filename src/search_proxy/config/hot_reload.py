"""
Hot-reload configuration support for Thai Search Proxy.

This module provides functionality to watch configuration files and
automatically reload settings without restarting the service.
"""

import os
import json
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from ...utils.logging import get_structured_logger
from .settings import SearchProxySettings, TokenizationConfig, RankingConfig

logger = get_structured_logger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """
    File system event handler for configuration file changes.
    """
    
    def __init__(self, config_manager: 'HotReloadConfigManager'):
        self.config_manager = config_manager
        self.last_reload_time = {}
        self.reload_delay = 1.0  # Debounce delay in seconds
        
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's a config file we care about
        if file_path.suffix in ['.json', '.yaml', '.yml', '.env']:
            # Debounce rapid changes
            current_time = datetime.now().timestamp()
            last_time = self.last_reload_time.get(str(file_path), 0)
            
            if current_time - last_time < self.reload_delay:
                return
                
            self.last_reload_time[str(file_path)] = current_time
            
            logger.info(f"Configuration file changed: {file_path}")
            
            # Schedule reload
            asyncio.create_task(
                self.config_manager.reload_configuration(str(file_path))
            )


class HotReloadConfigManager:
    """
    Manages hot-reloading of configuration files.
    
    Watches configuration files for changes and automatically
    reloads settings without service restart.
    """
    
    def __init__(self, settings: SearchProxySettings):
        self.settings = settings
        self.observers: List[Observer] = []
        self.reload_callbacks: List[Callable] = []
        self.config_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._running = False
        
        # Configuration paths to watch
        self.config_paths = {
            "settings": os.getenv("SEARCH_PROXY_CONFIG_PATH", "config/search_proxy.json"),
            "tokenization": os.getenv("TOKENIZATION_CONFIG_PATH", "config/tokenization.yaml"),
            "ranking": os.getenv("RANKING_CONFIG_PATH", "config/ranking.yaml"),
            "dictionary": os.getenv("CUSTOM_DICTIONARY_PATH", "data/dictionaries/thai_compounds.json"),
            "env": ".env"
        }
        
    def start(self):
        """Start watching configuration files."""
        if self._running:
            logger.warning("Hot reload already running")
            return
            
        logger.info("Starting hot reload configuration manager")
        
        # Create observers for each config directory
        watched_dirs = set()
        
        for config_type, config_path in self.config_paths.items():
            if not config_path:
                continue
                
            path = Path(config_path)
            
            # Watch parent directory
            parent_dir = path.parent
            if parent_dir not in watched_dirs:
                watched_dirs.add(parent_dir)
                
                # Create observer
                observer = Observer()
                event_handler = ConfigFileHandler(self)
                observer.schedule(event_handler, str(parent_dir), recursive=False)
                observer.start()
                
                self.observers.append(observer)
                
                logger.info(f"Watching directory: {parent_dir}")
        
        self._running = True
        logger.info("Hot reload configuration manager started")
        
    def stop(self):
        """Stop watching configuration files."""
        if not self._running:
            return
            
        logger.info("Stopping hot reload configuration manager")
        
        for observer in self.observers:
            observer.stop()
            observer.join()
            
        self.observers.clear()
        self._running = False
        
        logger.info("Hot reload configuration manager stopped")
        
    def register_reload_callback(self, callback: Callable):
        """
        Register a callback to be called when configuration is reloaded.
        
        Args:
            callback: Function to call on configuration reload
        """
        self.reload_callbacks.append(callback)
        logger.debug(f"Registered reload callback: {callback.__name__}")
        
    async def reload_configuration(self, file_path: str):
        """
        Reload configuration from changed file.
        
        Args:
            file_path: Path to the changed configuration file
        """
        try:
            with self._lock:
                # Determine config type
                config_type = self._get_config_type(file_path)
                
                if not config_type:
                    logger.debug(f"Ignoring non-config file: {file_path}")
                    return
                    
                logger.info(f"Reloading {config_type} configuration from {file_path}")
                
                # Load and validate new configuration
                if config_type == "dictionary":
                    await self._reload_dictionary(file_path)
                elif config_type == "tokenization":
                    await self._reload_tokenization_config(file_path)
                elif config_type == "ranking":
                    await self._reload_ranking_config(file_path)
                elif config_type == "env":
                    await self._reload_env_config(file_path)
                elif config_type == "settings":
                    await self._reload_settings(file_path)
                    
                # Notify callbacks
                for callback in self.reload_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(config_type)
                        else:
                            callback(config_type)
                    except Exception as e:
                        logger.error(f"Error in reload callback: {e}")
                        
                logger.info(f"Successfully reloaded {config_type} configuration")
                
        except Exception as e:
            logger.error(f"Failed to reload configuration from {file_path}: {e}")
            
    def _get_config_type(self, file_path: str) -> Optional[str]:
        """Determine configuration type from file path."""
        file_path = Path(file_path)
        
        for config_type, config_path in self.config_paths.items():
            if config_path and Path(config_path).resolve() == file_path.resolve():
                return config_type
                
        # Check by filename patterns
        if "dictionary" in file_path.name or "compounds" in file_path.name:
            return "dictionary"
        elif "tokenization" in file_path.name:
            return "tokenization"
        elif "ranking" in file_path.name:
            return "ranking"
        elif file_path.name == ".env":
            return "env"
            
        return None
        
    async def _reload_dictionary(self, file_path: str):
        """Reload custom dictionary."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract compound words
            compounds = []
            if isinstance(data, list):
                compounds = data
            elif isinstance(data, dict):
                for category, words in data.items():
                    if isinstance(words, list):
                        compounds.extend(words)
                        
            # Update cache
            self.config_cache["dictionary"] = compounds
            
            logger.info(f"Reloaded {len(compounds)} compound words from dictionary")
            
        except Exception as e:
            logger.error(f"Failed to reload dictionary: {e}")
            raise
            
    async def _reload_tokenization_config(self, file_path: str):
        """Reload tokenization configuration."""
        try:
            # Load YAML config
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            # Validate and update
            new_config = TokenizationConfig(**config_data)
            self.settings.tokenization = new_config
            
            logger.info("Reloaded tokenization configuration")
            
        except Exception as e:
            logger.error(f"Failed to reload tokenization config: {e}")
            raise
            
    async def _reload_ranking_config(self, file_path: str):
        """Reload ranking configuration."""
        try:
            # Load YAML config
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            # Validate and update
            new_config = RankingConfig(**config_data)
            self.settings.ranking = new_config
            
            logger.info("Reloaded ranking configuration")
            
        except Exception as e:
            logger.error(f"Failed to reload ranking config: {e}")
            raise
            
    async def _reload_env_config(self, file_path: str):
        """Reload environment variables."""
        try:
            # Load .env file
            from dotenv import load_dotenv
            load_dotenv(file_path, override=True)
            
            # Update settings from environment
            self.settings = SearchProxySettings()
            
            logger.info("Reloaded environment configuration")
            
        except Exception as e:
            logger.error(f"Failed to reload env config: {e}")
            raise
            
    async def _reload_settings(self, file_path: str):
        """Reload main settings file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # Validate and update
            new_settings = SearchProxySettings(**config_data)
            
            # Update current settings
            self.settings.tokenization = new_settings.tokenization
            self.settings.search = new_settings.search
            self.settings.ranking = new_settings.ranking
            self.settings.performance = new_settings.performance
            
            logger.info("Reloaded main settings configuration")
            
        except Exception as e:
            logger.error(f"Failed to reload settings: {e}")
            raise
            
    def get_cached_config(self, config_type: str) -> Optional[Any]:
        """
        Get cached configuration data.
        
        Args:
            config_type: Type of configuration to retrieve
            
        Returns:
            Cached configuration data or None
        """
        return self.config_cache.get(config_type)
        
    def get_config_status(self) -> Dict[str, Any]:
        """Get status of configuration monitoring."""
        return {
            "running": self._running,
            "watched_paths": self.config_paths,
            "observers_active": len(self.observers),
            "registered_callbacks": len(self.reload_callbacks),
            "cached_configs": list(self.config_cache.keys())
        }