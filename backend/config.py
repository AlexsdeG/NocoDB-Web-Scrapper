from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

class UrlCleaningConfig(BaseModel):
    """Configuration for URL cleaning."""
    base_pattern: str = Field(..., description="Base URL pattern")
    extract_pattern: str = Field(..., description="Regex pattern to extract ID")
    clean_pattern: str = Field(..., description="Clean URL pattern")

class SelectorConfig(BaseModel):
    """Configuration for a CSS selector."""
    type: str = Field(..., description="Type of selector: id, class, css, xpath")
    value: str = Field(..., description="Selector value")

class NocoDBFieldConfig(BaseModel):
    """Configuration for a NocoDB field."""
    id: str = Field(..., description="NocoDB field ID")
    type: str = Field(..., description="Field type: map, input_url, nocodb_email")
    duplicate_check: Optional[bool] = Field(False, description="Whether to check for duplicates")

class ScraperConfig(BaseModel):
    """Configuration for a website scraper."""
    nocodb_field_map: Dict[str, NocoDBFieldConfig] = Field(..., description="Map NocoDB field names to field configurations")
    selectors: Dict[str, SelectorConfig] = Field(..., description="Selectors for data extraction")
    url_cleaning: Optional[UrlCleaningConfig] = Field(None, description="URL cleaning configuration")

class AppConfig(BaseModel):
    """Main application configuration."""
    app_name: str = Field(..., description="Application name")
    app_description: str = Field(..., description="Application description")
    signup_secret: str = Field(..., description="Secret for user signup")
    frontend_config: Dict[str, Any] = Field(..., description="Frontend configuration")

class ConfigManager:
    """Manages loading and validating configuration files."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._config: Optional[AppConfig] = None
        self._scrapers: Optional[Dict[str, ScraperConfig]] = None
        self._scrapers_raw: Optional[Dict[str, Any]] = None
        self._login_data: Optional[Dict[str, str]] = None
        self._user_map: Optional[Dict[str, str]] = None
        self._ux_config: Optional[Dict[str, Any]] = None
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Check and log permissions
        self._check_permissions()
    
    def _check_permissions(self) -> None:
        """Check if the data directory is writable."""
        try:
            # Try to create a test file
            test_file = self.data_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            logger.info(f"Data directory {self.data_dir} is writable")
        except Exception as e:
            logger.warning(f"Data directory {self.data_dir} may not be writable: {e}")
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load a JSON file."""
        file_path = self.data_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            raise
    
    def _save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """Save data to a JSON file."""
        file_path = self.data_dir / filename
        
        try:
            # Write to a temporary file first
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomically replace the original file
            temp_file.replace(file_path)
            logger.info(f"Successfully saved {filename}")
            
        except PermissionError as e:
            logger.error(f"Permission denied when saving {filename}: {e}")
            raise PermissionError(f"Cannot write to {file_path}. Please check file permissions.")
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
            raise
    
    @property
    def config(self) -> AppConfig:
        """Get the main application configuration."""
        if self._config is None:
            config_data = self._load_json("config.json")
            self._config = AppConfig(**config_data)
        return self._config
    
    @property
    def scrapers(self) -> Dict[str, ScraperConfig]:
        """Get the scraper configurations."""
        if self._scrapers is None:
            scrapers_data = self._load_json("scrapers.json")
            self._scrapers = {
                domain: ScraperConfig(**config)
                for domain, config in scrapers_data.items()
            }
        return self._scrapers
    
    @property
    def scrapers_raw(self) -> Dict[str, Any]:
        """Get the raw scraper configurations."""
        if self._scrapers_raw is None:
            self._scrapers_raw = self._load_json("scrapers.json")
        return self._scrapers_raw
    
    @property
    def login_data(self) -> Dict[str, str]:
        """Get the login credentials."""
        if self._login_data is None:
            self._login_data = self._load_json("login.json")
        return self._login_data
    
    def save_login_data(self, data: Dict[str, str]) -> None:
        """Save login credentials."""
        self._save_json("login.json", data)
        self._login_data = data
    
    @property
    def user_map(self) -> Dict[str, str]:
        """Get the user email mappings."""
        if self._user_map is None:
            self._user_map = self._load_json("user_map.json")
        return self._user_map
    
    def save_user_map(self, data: Dict[str, str]) -> None:
        """Save user email mappings."""
        self._save_json("user_map.json", data)
        self._user_map = data
    
    @property
    def ux_config(self) -> Dict[str, Any]:
        """Get the UX configuration."""
        if self._ux_config is None:
            self._ux_config = self._load_json("ux.json")
        return self._ux_config
    
    def get_scraper_config(self, domain: str) -> Optional[ScraperConfig]:
        """Get scraper configuration for a specific domain."""
        return self.scrapers.get(domain)
    
    def get_duplicate_check_fields(self, domain: str) -> list[str]:
        """Get list of field IDs that should be checked for duplicates."""
        scraper_config = self.get_scraper_config(domain)
        if not scraper_config:
            return []
        
        duplicate_fields = []
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.duplicate_check:
                duplicate_fields.append(field_config.id)
        
        return duplicate_fields
    
    def get_field_config_by_id(self, domain: str, field_id: str) -> Optional[NocoDBFieldConfig]:
        """Get field configuration by NocoDB field ID."""
        scraper_config = self.get_scraper_config(domain)
        if not scraper_config:
            return None
        
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.id == field_id:
                return field_config
        
        return None
    
    def reload_configs(self) -> None:
        """Reload all configuration files."""
        self._config = None
        self._scrapers = None
        self._scrapers_raw = None
        self._login_data = None
        self._user_map = None
        self._ux_config = None