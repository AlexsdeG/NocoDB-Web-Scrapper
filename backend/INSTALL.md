# Installation Guide

## Quick Setup

1. **Navigate to the backend directory:**
   ```bash
   cd NocoDB_Web_Scrapper/backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   
   # On Linux/Mac:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

5. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your actual values:
   - Get NocoDB API token from your NocoDB instance
   - Get Project ID and Table ID from your NocoDB URL
   - Generate a strong JWT secret key: `openssl rand -base64 32`

6. **Test the setup:**
   ```bash
   python test_setup.py
   ```

7. **Start the server:**
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8091` with documentation at `http://localhost:8091/docs`.

## Default Credentials

- **Username**: `admin`
- **Password**: `admin123`

## Testing with curl

1. **Get access token:**
   ```bash
   curl -X POST "http://localhost:8091/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin123"
   ```

2. **Check status:**
   ```bash
   curl "http://localhost:8091/status"
   ```

3. **Test scraping (replace TOKEN and URL):**
   ```bash
   curl -X POST "http://localhost:8091/scrape" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/listing"}'
   ```