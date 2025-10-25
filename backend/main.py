from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
import os
import json
import requests
from datetime import timedelta
from urllib.parse import urlparse

from auth import (
    verify_password, get_password_hash, create_access_token, 
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from config import ConfigManager
from scraper import (
    scrape_apartment_data, extract_domain_from_url, 
    clean_url_with_scraper_config
)

# Initialize FastAPI app
app = FastAPI(
    title="NocoDB Web Scraper API",
    description="API for scraping web data and populating NocoDB",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize configuration manager
config_manager = ConfigManager()

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class ScrapeRequest(BaseModel):
    url: str

class ScrapeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class SignupRequest(BaseModel):
    username: str
    password: str
    nocodb_email: EmailStr
    signup_secret: str

class UserUpdateRequest(BaseModel):
    new_password: Optional[str] = None
    nocodb_email: Optional[EmailStr] = None

class StatusResponse(BaseModel):
    api_status: str
    nocodb_status: str
    message: str

# Utility functions
def get_nocodb_headers() -> Dict[str, str]:
    """Get headers for NocoDB API requests."""
    return {
        "xc-token": os.getenv("NOCODB_API_TOKEN"),
        "Content-Type": "application/json"
    }

def get_nocodb_url() -> str:
    """Get NocoDB base URL."""
    return os.getenv("NOCODB_URL", "").rstrip('/')

def get_nocodb_table_url() -> str:
    """Get NocoDB table API URL."""
    base_url = get_nocodb_url()
    project_id = os.getenv("NOCODB_PROJECT_ID")
    table_id = os.getenv("NOCODB_TABLE_ID")
    
    if not all([base_url, project_id, table_id]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="NocoDB configuration incomplete"
        )
    
    return f"{base_url}/api/v2/tables/{table_id}/records"

def check_existing_url(url: str, url_field_id: str) -> Optional[Dict[str, Any]]:
    """Check if a URL already exists in NocoDB."""
    try:
        from urllib.parse import quote
        table_url = get_nocodb_table_url()
        headers = get_nocodb_headers()
        
        # Use exact match filter: (fieldId,eq,value)
        # NocoDB filter format: where=(field,operator,value)
        where_clause = f"where=({url_field_id},eq,{quote(url)})"
        print("DEBUG: Checking existing URL with filter clause:", where_clause)
        
        response = requests.get(f"{table_url}?{where_clause}", headers=headers)
        print("DEBUG: NocoDB response status:", response.status_code)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("list", [])
            print("DEBUG: NocoDB response data:", json.dumps(data, indent=2))
            if records:
                return records[0]  # Return the first matching record
        else:
            print("DEBUG: NocoDB response text:", response.text)
        
        return None
        
    except Exception as e:
        # Log error but don't fail the scraping process
        print(f"Error checking existing URL: {e}")
        return None

# API Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return access token."""
    username = form_data.username
    password = form_data.password
    
    # Verify credentials
    login_data = config_manager.login_data
    if username not in login_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(password, login_data[username]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(
    request: ScrapeRequest,
    current_user: str = Depends(get_current_user)
):
    """Scrape data from a URL and add it to NocoDB."""
    try:
        # Extract domain and get scraper configuration first
        domain = extract_domain_from_url(request.url)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract domain from URL"
            )
        
        scraper_config = config_manager.get_scraper_config(domain)
        if not scraper_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No scraper configuration found for domain: {domain}"
            )
        
        # Clean URL using scraper-specific configuration
        cleaned_url = clean_url_with_scraper_config(request.url, scraper_config.model_dump())
        
        # Validate cleaned URL
        parsed_url = urlparse(cleaned_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Check if cleaned URL already exists in NocoDB
        url_field_id = scraper_config.nocodb_field_map.get("url_address")
        if url_field_id:
            print("DEBUG: Checking for existing URL in NocoDB", cleaned_url, url_field_id)
            existing_record = check_existing_url(cleaned_url, url_field_id)
            if existing_record:
                return ScrapeResponse(
                    success=False,
                    message=f"Listing already exists in database. Found at ID: {existing_record.get('Id')}",
                    data={"existing_record": existing_record, "cleaned_url": cleaned_url}
                )
        
        # Scrape the data using cleaned URL and pass full scrapers config
        scraped_data = await scrape_apartment_data(
            request.url, 
            scraper_config.model_dump(),
            config_manager.scrapers_raw  # Changed from scrapers_data to scrapers_raw
        )
        
        # Map field names to NocoDB field names
        nocodb_data = {}
        field_map = scraper_config.nocodb_field_map
        
        for internal_name, nocodb_field in field_map.items():
            if internal_name in scraped_data:
                nocodb_data[nocodb_field] = scraped_data[internal_name]
        
        # Add URL address field (use cleaned URL)
        url_field_id = field_map.get("url_address")
        if url_field_id:
            nocodb_data[url_field_id] = cleaned_url
        
        # Add found_by field with user email
        found_by_field_id = field_map.get("found_by")
        user_map = config_manager.user_map
        user_email = user_map.get(current_user)
        if found_by_field_id and user_email:
            nocodb_data[found_by_field_id] = user_email
        elif user_email:
            # Fallback to CreatedBy field if found_by is not configured
            nocodb_data["CreatedBy"] = [{"email": user_email}]
        
        # Send data to NocoDB
        table_url = get_nocodb_table_url()
        headers = get_nocodb_headers()
        
        response = requests.post(table_url, json=nocodb_data, headers=headers)
        
        if response.status_code not in [200, 201]:
            error_detail = f"NocoDB API error: {response.status_code} - {response.text}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
        
        return ScrapeResponse(
            success=True,
            message="Data successfully scraped and added to NocoDB",
            data=scraped_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scraping failed: {str(e)}"
        )

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get API and NocoDB connection status."""
    try:
        # Check NocoDB connection
        try:
            table_url = get_nocodb_table_url()
            headers = get_nocodb_headers()
            
            # Try to fetch a single record to test connection
            response = requests.get(f"{table_url}?limit=1", headers=headers)
            
            if response.status_code == 200:
                nocodb_status = "connected"
                nocodb_message = "Successfully connected to NocoDB"
            else:
                nocodb_status = "error"
                nocodb_message = f"NocoDB API error: {response.status_code}"
                
        except Exception as e:
            nocodb_status = "disconnected"
            nocodb_message = f"Cannot connect to NocoDB: {str(e)}"
        
        return StatusResponse(
            api_status="running",
            nocodb_status=nocodb_status,
            message=f"API is running. {nocodb_message}"
        )
        
    except Exception as e:
        return StatusResponse(
            api_status="error",
            nocodb_status="unknown",
            message=f"Status check failed: {str(e)}"
        )

@app.post("/signup")
async def signup_user(request: SignupRequest):
    """Register a new user."""
    try:
        # Verify signup secret
        if request.signup_secret != config_manager.config.signup_secret:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signup secret"
            )
        
        # Check if username already exists
        login_data = config_manager.login_data
        if request.username in login_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Hash password and save user
        hashed_password = get_password_hash(request.password)
        
        # Update login data
        login_data[request.username] = hashed_password
        config_manager.save_login_data(login_data)
        
        # Update user map
        user_map = config_manager.user_map
        user_map[request.username] = request.nocodb_email
        config_manager.save_user_map(user_map)
        
        return {"message": "User successfully registered"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {str(e)}"
        )

@app.put("/users/me")
async def update_user(
    request: UserUpdateRequest,
    current_user: str = Depends(get_current_user)
):
    """Update current user's information."""
    try:
        # Update password if provided
        if request.new_password:
            login_data = config_manager.login_data
            login_data[current_user] = get_password_hash(request.new_password)
            config_manager.save_login_data(login_data)
        
        # Update email if provided
        if request.nocodb_email:
            user_map = config_manager.user_map
            user_map[current_user] = request.nocodb_email
            config_manager.save_user_map(user_map)
        
        return {"message": "User information updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )

@app.post("/validate-email")
async def validate_nocodb_email(
    email: EmailStr,
    current_user: str = Depends(get_current_user)
):
    """Validate if a NocoDB user exists with the given email."""
    try:
        # This would require NocoDB admin API access
        # For now, we'll just return a placeholder response
        return {"valid": True, "message": "Email validation placeholder"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email validation failed: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "NocoDB Web Scraper API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Serve static files (for frontend)
# app.mount("/static", StaticFiles(directory="frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    
    # Check required environment variables
    required_vars = ["NOCODB_API_TOKEN", "NOCODB_URL", "NOCODB_PROJECT_ID", "NOCODB_TABLE_ID", "JWT_SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these variables in your .env file or environment.")
        exit(1)
    
    uvicorn.run(app, host="0.0.0.0", port=8091)