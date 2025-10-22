# NocoDB Web Scraper

A secure, multi-user web application that allows authorized users to automatically scrape data from various websites and populate it into a shared NocoDB database. The system is highly configurable via JSON files for easy maintenance and expansion.

## Features

- **Secure Authentication**: JWT-based authentication with password hashing
- **Multi-User Support**: Each user can have their own NocoDB email mapping
- **Configurable Scraping**: JSON-based configuration for different websites
- **Real-time Status**: API and NocoDB connection status monitoring
- **Extensible Design**: Easy to add new websites and data fields
- **General Purpose**: Can be adapted for any website, not just real estate

## Phase 1: Backend Foundation & Core Scraping (MVP)

This phase implements the complete backend API with core scraping functionality.

### Prerequisites

- Python 3.8+
- NocoDB instance with API access
- Playwright browsers

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd NocoDB_Web_Scrapper/backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
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
   
   Edit `.env` and fill in your configuration:
   ```env
   # NocoDB Configuration
   NOCODB_API_TOKEN=your_nocodb_api_token_here
   NOCODB_URL=https://your-nocodb-instance.com
   NOCODB_PROJECT_ID=your_project_id_here
   NOCODB_TABLE_ID=your_table_id_here
   
   # JWT Configuration
   JWT_SECRET_KEY=your_super_secret_jwt_key_at_least_32_characters_long
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   
   # Application Configuration
   APP_NAME=NocoDB Web Scraper
   DEBUG=false
   ```

### Configuration

#### NocoDB Setup

1. **Get your NocoDB API Token:**
   - Go to your NocoDB instance
   - Navigate to Account Settings → API Tokens
   - Create a new token with read/write permissions

2. **Get Project and Table IDs:**
   - Open your NocoDB project
   - Navigate to the table you want to populate
   - The URL will contain the project and table IDs:
     ```
     https://your-nocodb.com/nc/project_id/table_id
     ```

#### Application Configuration

Edit the JSON files in the `data/` directory:

- **`data/config.json`**: Main application settings
- **`data/login.json`**: User credentials (passwords are hashed)
- **`data/user_map.json`**: Maps usernames to NocoDB emails
- **`data/scrapers.json`**: Website-specific scraping configurations

#### Default User

The application comes with a default user:
- **Username**: `admin`
- **Password**: `admin123`

You can change this by updating the hash in `data/login.json` or creating new users via the API.

### Running the Application

1. **Start the server:**
   ```bash
   python main.py
   ```

2. **The API will be available at:** `http://localhost:8091`

3. **API Documentation:** `http://localhost:8091/docs`

### API Endpoints

#### Authentication

- **POST `/token`**: Login and get access token
  ```bash
  curl -X POST "http://localhost:8091/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin&password=admin123"
  ```

#### Scraping

- **POST `/scrape`**: Scrape a URL and add to NocoDB (requires authentication)
  ```bash
  curl -X POST "http://localhost:8091/scrape" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"url": "https://www.immoscout24.de/expose/123456"}'
  ```

#### Status

- **GET `/status`**: Check API and NocoDB connection status
  ```bash
  curl "http://localhost:8091/status"
  ```

#### User Management

- **POST `/signup`**: Register a new user
  ```bash
  curl -X POST "http://localhost:8091/signup" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "newuser",
      "password": "password123",
      "nocodb_email": "user@example.com",
      "signup_secret": "your-signup-secret"
    }'
  ```

- **PUT `/users/me`**: Update user information (requires authentication)
  ```bash
  curl -X PUT "http://localhost:8091/users/me" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"nocodb_email": "newemail@example.com"}'
  ```

### Adding New Websites

To add support for a new website, update `data/scrapers.json`:

```json
{
  "www.example.com": {
    "nocodb_field_map": {
      "Title": "title",
      "Price": "price",
      "Description": "description"
    },
    "selectors": {
      "title": {"type": "css", "value": "h1.title"},
      "price": {"type": "css", "value": ".price"},
      "description": {"type": "css", "value": ".description"}
    }
  }
}
```

#### Selector Types

- **`id`**: Find element by ID
- **`class`**: Find element by class name
- **`css`**: CSS selector
- **`xpath`**: XPath expression (limited support)

### NocoDB Table Structure

Your NocoDB table should have columns that match the `nocodb_field_map` in your scraper configuration. For the default real estate scrapers:

- `Title` (SingleLineText)
- `Warmmiete` (Currency)
- `Kaution` (Currency)
- `Area_m2` (Number)
- `Rooms` (Number)
- `Address` (SingleLineText)
- `URL` (SingleLineText)
- `CreatedBy` (LinkToAnotherRecord → Users table)

### Security Considerations

- The JWT secret key should be a long, random string
- Change the default admin password immediately
- Use HTTPS in production
- Restrict CORS origins appropriately
- Keep your NocoDB API token secure

### Troubleshooting

#### Common Issues

1. **"NocoDB configuration incomplete"**: Check your `.env` file for missing variables
2. **"No scraper configuration found"**: Add the website domain to `scrapers.json`
3. **"Could not extract field"**: Check the CSS selectors in the scraper configuration
4. **Playwright browser issues**: Run `playwright install` to install browsers

#### Debug Mode

Set `DEBUG=true` in your `.env` file to enable detailed logging.

### Development

#### Project Structure

```
backend/
├── main.py              # FastAPI application
├── auth.py              # Authentication logic
├── config.py            # Configuration management
├── scraper.py           # Web scraping logic
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── data/               # Configuration files
    ├── config.json     # App settings
    ├── login.json      # User credentials
    ├── user_map.json   # User email mappings
    └── scrapers.json   # Website configurations
```

#### Adding New Features

1. **New Selector Types**: Extend the `_extract_with_selector` method in `scraper.py`
2. **Data Processing**: Add post-processing logic in the `scrape_apartment_data` method
3. **API Endpoints**: Add new routes in `main.py`
4. **Authentication**: Extend `auth.py` for additional security features

## Next Phases

- **Phase 2**: Frontend UI with user self-service
- **Phase 3**: Advanced features and full generalization

## License

This project is open source. Please refer to the license file for details.

## Support

For issues and questions, please create an issue in the project repository.