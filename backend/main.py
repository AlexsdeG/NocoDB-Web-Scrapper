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
from scraper import scrape_apartment_data, extract_domain_from_url, clean_url_with_scraper_config

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
    repassword: str
    nocodb_email: EmailStr
    signup_secret: str

class UserUpdateRequest(BaseModel):
    new_password: Optional[str] = None
    nocodb_email: Optional[EmailStr] = None

class StatusResponse(BaseModel):
    api_status: str
    nocodb_status: str
    message: str

class CheckURLRequest(BaseModel):
    url: str
    mode: str = "scraper"  # scraper, manual, api

class CheckURLResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class SaveDataRequest(BaseModel):
    url: str
    mode: str
    data: Dict[str, Any]

class SaveDataResponse(BaseModel):
    success: bool
    message: str
    record_id: Optional[str] = None

class UXConfigResponse(BaseModel):
    success: bool
    config: Dict[str, Any]
    
class DeleteRecordRequest(BaseModel):
    record_id: str

class DeleteRecordResponse(BaseModel):
    success: bool
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
        
        response = requests.get(f"{table_url}?{where_clause}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("list", [])
            if records:
                return records[0]  # Return the first matching record
        
        return None
        
    except Exception as e:
        # Log error but don't fail the scraping process
        print(f"Error checking existing URL: {e}")
        return None

# API Routes
@app.get("/ux-config", response_model=UXConfigResponse)
async def get_ux_config(current_user: str = Depends(get_current_user)):
    """Get UX configuration for frontend."""
    try:
        return UXConfigResponse(
            success=True,
            config=config_manager.ux_config
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load UX configuration: {str(e)}"
        )

@app.post("/check-url", response_model=CheckURLResponse)
async def check_url(
    request: CheckURLRequest,
    current_user: str = Depends(get_current_user)
):
    """Check URL validity and domain support."""
    try:
        url = request.url
        mode = request.mode
        
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return CheckURLResponse(
                success=False,
                message="Invalid URL format"
            )
        
        # Extract domain and get scraper configuration
        domain = extract_domain_from_url(url)
        if not domain:
            return CheckURLResponse(
                success=False,
                message="Could not extract domain from URL"
            )
        
        scraper_config = config_manager.get_scraper_config(domain)
        if not scraper_config:
            return CheckURLResponse(
                success=False,
                message=f"No scraper configuration found for domain: {domain}"
            )
        
        # Clean URL using scraper-specific configuration
        cleaned_url = clean_url_with_scraper_config(url, scraper_config.model_dump())
        
        # Check if URL already exists in NocoDB using cleaned URL
        url_field_config = None
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.type == "input_url":
                url_field_config = field_config
                break
        
        if url_field_config:
            existing_record = check_existing_url(cleaned_url, url_field_config.id)
            if existing_record:
                return CheckURLResponse(
                    success=False,
                    message=f"Listing already exists in database. Found at ID: {existing_record.get('Id')}",
                    data={"existing_record": existing_record, "cleaned_url": cleaned_url}
                )
        
        # If mode is scraper, try to scrape data
        scraped_data = {}
        if mode == "scraper":
            try:
                scraped_data = await scrape_apartment_data(cleaned_url, scraper_config.model_dump(), config_manager.scrapers_raw)
            except Exception as e:
                # If scraping fails, return error but allow manual input
                return CheckURLResponse(
                    success=False,
                    message=f"Scraping failed: {str(e)}. You can switch to manual mode.",
                    data={"scraping_failed": True, "domain": domain, "cleaned_url": cleaned_url}
                )
        
        return CheckURLResponse(
            success=True,
            message="URL is valid and ready for processing",
            data={
                "domain": domain,
                "scraped_data": scraped_data,
                "mode": mode,
                "cleaned_url": cleaned_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL check failed: {str(e)}"
        )

@app.post("/save-data", response_model=SaveDataResponse)
async def save_data(
    request: SaveDataRequest,
    current_user: str = Depends(get_current_user)
):
    """Save processed data to NocoDB."""
    try:
        url = request.url
        mode = request.mode
        data = request.data
        
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Extract domain and get scraper configuration
        domain = extract_domain_from_url(url)
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
        cleaned_url = clean_url_with_scraper_config(url, scraper_config.model_dump())
        
        # Final check if URL already exists in NocoDB using cleaned URL
        url_field_config = None
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.type == "input_url":
                url_field_config = field_config
                break
        
        if url_field_config:
            existing_record = check_existing_url(cleaned_url, url_field_config.id)
            if existing_record:
                return SaveDataResponse(
                    success=False,
                    message=f"Listing already exists in database. Found at ID: {existing_record.get('Id')}"
                )
        
        # Build NocoDB data dynamically based on field configurations
        nocodb_data = {}
        user_map = config_manager.user_map
        user_email = user_map.get(current_user)
        
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.type == "map":
                # Map scraped data - only add if value exists and is not empty
                if field_name in data:
                    value = data[field_name]
                    # Skip empty strings, None, and whitespace-only strings
                    if value is not None and str(value).strip() != "":
                        nocodb_data[field_config.id] = value
            elif field_config.type == "input_url":
                # Use cleaned URL
                nocodb_data[field_config.id] = cleaned_url
            elif field_config.type == "nocodb_email":
                # Use user email
                if user_email:
                    nocodb_data[field_config.id] = user_email
        
        # Fallback to CreatedBy field if no found_by field is configured
        if not any(fc.type == "nocodb_email" for fc in scraper_config.nocodb_field_map.values()) and user_email:
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
        
        # Get the record ID from response and convert to string
        response_data = response.json()
        record_id = response_data.get("Id") or response_data.get("id")
        record_id_str = str(record_id) if record_id is not None else None
        
        return SaveDataResponse(
            success=True,
            message="Data successfully saved to NocoDB",
            record_id=record_id_str
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Save failed: {str(e)}"
        )
        
@app.delete("/delete-record", response_model=DeleteRecordResponse)
async def delete_record(
    request: DeleteRecordRequest,
    current_user: str = Depends(get_current_user)
):
    """Delete a record from NocoDB by ID."""
    try:
        record_id = request.record_id
        
        if not record_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Record ID is required"
            )
        
        # Get NocoDB table URL and headers
        table_url = get_nocodb_table_url()
        headers = get_nocodb_headers()
        
        # Delete the record using the NocoDB API
        # According to the screenshot, we need to send an array of record IDs
        delete_data = [{"Id": int(record_id)}]
        
        response = requests.delete(table_url, json=delete_data, headers=headers)
        
        if response.status_code not in [200, 204]:
            error_detail = f"NocoDB API error: {response.status_code} - {response.text}"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )
        
        return DeleteRecordResponse(
            success=True,
            message="Record successfully deleted from NocoDB"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Delete failed: {str(e)}"
        )

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
        url = request.url
        
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Extract domain and get scraper configuration
        domain = extract_domain_from_url(url)
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
        cleaned_url = clean_url_with_scraper_config(url, scraper_config.model_dump())
        
        # Validate cleaned URL
        parsed_url = urlparse(cleaned_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format after cleaning"
            )
        
        # Check if cleaned URL already exists in NocoDB
        url_field_config = None
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.type == "input_url":
                url_field_config = field_config
                break
        
        if url_field_config:
            existing_record = check_existing_url(cleaned_url, url_field_config.id)
            if existing_record:
                return ScrapeResponse(
                    success=False,
                    message=f"Listing already exists in database. Found at ID: {existing_record.get('Id')}",
                    data={"existing_record": existing_record}
                )
        
        # Scrape the data
        scraped_data = await scrape_apartment_data(cleaned_url, scraper_config.model_dump(), config_manager.scrapers_raw)
        
        # Build NocoDB data dynamically based on field configurations
        nocodb_data = {}
        user_map = config_manager.user_map
        user_email = user_map.get(current_user)
        
        # Iterate over all fields in the scraper configuration
        for field_name, field_config in scraper_config.nocodb_field_map.items():
            if field_config.type == "map":
                # Map scraped data to NocoDB field - only add if value exists and is not empty
                if field_name in scraped_data:
                    value = scraped_data[field_name]
                    # Skip empty strings, None, and whitespace-only strings
                    if value is not None and str(value).strip() != "":
                        nocodb_data[field_config.id] = value
                    
            elif field_config.type == "input_url":
                # Use cleaned URL for URL field
                nocodb_data[field_config.id] = cleaned_url
                
            elif field_config.type == "nocodb_email":
                # Use current user's email for email fields
                if user_email:
                    nocodb_data[field_config.id] = user_email
        
        # Fallback to CreatedBy field if no nocodb_email fields are configured
        if not any(fc.type == "nocodb_email" for fc in scraper_config.nocodb_field_map.values()) and user_email:
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
        
        # Get the record ID from response and convert to string
        response_data = response.json()
        record_id = response_data.get("Id") or response_data.get("id")
        record_id_str = str(record_id) if record_id is not None else None
        
        return ScrapeResponse(
            success=True,
            message="Data successfully scraped and added to NocoDB",
            data={
                "scraped_data": scraped_data,
                "record_id": record_id_str,
                "cleaned_url": cleaned_url
            }
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
            
        # Check if passwords match
        if request.password != request.repassword:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Hash password and save user
        hashed_password = get_password_hash(request.password)
        
        # Update login data
        login_data[request.username] = hashed_password
        config_manager.save_login_data(login_data)
        
        # Update user map with lowercase email
        user_map = config_manager.user_map
        user_map[request.username] = request.nocodb_email.lower()
        config_manager.save_user_map(user_map)
        
        # Reload both to ensure in-memory cache matches files
        config_manager.reload_login_data()
        config_manager.reload_user_map()
        
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
        updated = False
        
        # Update password if provided
        if request.new_password:
            login_data = config_manager.login_data.copy()
            login_data[current_user] = get_password_hash(request.new_password)
            config_manager.save_login_data(login_data)
            # Reload to ensure in-memory cache is updated
            config_manager.reload_login_data()
            updated = True
        
        # Update email if provided
        if request.nocodb_email:
            user_map = config_manager.user_map.copy()
            # Normalize email to lowercase
            user_map[current_user] = request.nocodb_email.lower()
            config_manager.save_user_map(user_map)
            # Reload to ensure in-memory cache is updated
            config_manager.reload_user_map()
            updated = True
        
        if updated:
            return {"message": "User information updated successfully"}
        else:
            return {"message": "No changes were made"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )

@app.get("/users/me")
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user's information."""
    try:
        user_info = {
            "username": current_user,
            "nocodb_email": config_manager.user_map.get(current_user)
        }
        return {"user": user_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user information: {str(e)}"
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
    
    uvicorn.run(app, host="0.0.0.0", port=8000)