#!/usr/bin/env python3
"""
Test script to verify the backend setup.
This script checks if all required files and configurations are properly set up.
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path: str, description: str) -> bool:
    """Check if a file exists."""
    if os.path.exists(file_path):
        print(f"✓ {description}: {file_path}")
        return True
    else:
        print(f"✗ {description}: {file_path} (MISSING)")
        return False

def check_json_file(file_path: str, description: str) -> bool:
    """Check if a JSON file is valid."""
    if not os.path.exists(file_path):
        print(f"✗ {description}: {file_path} (MISSING)")
        return False
    
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        print(f"✓ {description}: {file_path} (valid JSON)")
        return True
    except json.JSONDecodeError as e:
        print(f"✗ {description}: {file_path} (invalid JSON: {e})")
        return False

def main():
    """Run setup verification."""
    print("=== NocoDB Web Scraper - Backend Setup Verification ===\n")
    
    # Check required files
    required_files = [
        ("main.py", "FastAPI application"),
        ("auth.py", "Authentication module"),
        ("config.py", "Configuration manager"),
        ("scraper.py", "Web scraper module"),
        ("requirements.txt", "Python dependencies"),
    ]
    
    print("Checking required files:")
    all_files_exist = True
    for file_name, description in required_files:
        if not check_file_exists(file_name, description):
            all_files_exist = False
    
    print()
    
    # Check data directory and JSON files
    print("Checking configuration files:")
    data_dir = Path("data")
    if not data_dir.exists():
        print("✗ Data directory: data/ (MISSING)")
        all_files_exist = False
    else:
        print("✓ Data directory: data/")
        
        config_files = [
            ("data/config.json", "Main configuration"),
            ("data/login.json", "User credentials"),
            ("data/user_map.json", "User email mappings"),
            ("data/scrapers.json", "Scraper configurations"),
        ]
        
        for file_name, description in config_files:
            if not check_json_file(file_name, description):
                all_files_exist = False
    
    print()
        
    # Check Python imports
    print("Checking Python module imports:")
    try:
        import auth
        print("✓ auth module imports successfully")
    except ImportError as e:
        print(f"✗ auth module import failed: {e}")
        all_files_exist = False
    
    try:
        import config
        print("✓ config module imports successfully")
    except ImportError as e:
        print(f"✗ config module import failed: {e}")
        all_files_exist = False
    
    try:
        import scraper
        print("✓ scraper module imports successfully")
    except ImportError as e:
        print(f"✗ scraper module import failed: {e}")
        all_files_exist = False
    
    print()
    
    # Summary
    if all_files_exist:
        print("🎉 All checks passed! The backend is properly set up.")
        print("\nNext steps:")
        print("1. Create a virtual environment: python -m venv venv")
        print("2. Activate it: source venv/bin/activate")
        print("3. Install dependencies: pip install -r requirements.txt")
        print("4. Install Playwright: playwright install")
        print("6. Run the server: python main.py")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())